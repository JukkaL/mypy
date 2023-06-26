// Generic native class attribute getters and setters

#include <Python.h>
#include "CPy.h"

PyObject *CPyAttr_UndefinedError(PyObject *self, CPyAttr_Context *context) {
    assert(!context->always_defined && "attribute should be initialized!");
    PyErr_Format(PyExc_AttributeError,
        "attribute '%s' of '%s' undefined", context->attr_name, Py_TYPE(self)->tp_name);
    return NULL;
}

int CPyAttr_UndeletableError(PyObject *self, CPyAttr_Context *context) {
    PyErr_Format(PyExc_AttributeError,
        "'%s' object attribute '%s' cannot be deleted", Py_TYPE(self)->tp_name, context->attr_name);
    return -1;
}

static void set_definedness_in_bitmap(PyObject *self, CPyAttr_Context *context, bool defined) {
    uint32_t *bitmap = (uint32_t *)((char *)self + context->bitmap.offset);
    if (defined) {
        *bitmap |= context->bitmap.mask;
    } else {
        *bitmap &= ~context->bitmap.mask;
    }
}

static inline bool is_undefined_via_bitmap(PyObject *self, CPyAttr_Context *context) {
    return !(*(uint32_t *)((char *)self + context->bitmap.offset) & context->bitmap.mask);
}

PyObject *CPyAttr_GetterPyObject(PyObject *self, CPyAttr_Context *context) {
    PyObject *value = *(PyObject **)((char *)self + context->offset);
    if (unlikely(value == NULL)) {
        return CPyAttr_UndefinedError(self, context);
    }
    return Py_NewRef(value);
}

PyObject *CPyAttr_GetterTagged(PyObject *self, CPyAttr_Context *context) {
    CPyTagged value = *(CPyTagged *)((char *)self + context->offset);
    if (unlikely(value == CPY_INT_TAG)) {
        return CPyAttr_UndefinedError(self, context);
    }
    return CPyTagged_AsObject(value);
}

PyObject *CPyAttr_GetterBool(PyObject *self, CPyAttr_Context *context) {
    char value = *((char *)self + context->offset);
    if (unlikely(value == 2)) {
        return CPyAttr_UndefinedError(self, context);
    }
    return Py_NewRef(value ? Py_True : Py_False);
}

PyObject *CPyAttr_GetterFloat(PyObject *self, CPyAttr_Context *context) {
    double value = *(double *)((char *)self + context->offset);
    if (unlikely(value == CPY_FLOAT_ERROR
            && !context->always_defined
            && is_undefined_via_bitmap(self, context))) {
        return CPyAttr_UndefinedError(self, context);
    }
    return PyFloat_FromDouble(value);
}

PyObject *CPyAttr_GetterInt16(PyObject *self, CPyAttr_Context *context) {
    int16_t value = *(int16_t *)((char *)self + context->offset);
    if (unlikely(value == CPY_LL_INT_ERROR
            && !context->always_defined
            && is_undefined_via_bitmap(self, context))) {
        return CPyAttr_UndefinedError(self, context);
    }
    return PyLong_FromLong(value);
}

PyObject *CPyAttr_GetterInt32(PyObject *self, CPyAttr_Context *context) {
    int32_t value = *(int32_t *)((char *)self + context->offset);
    if (unlikely(value == CPY_LL_INT_ERROR
            && !context->always_defined
            && is_undefined_via_bitmap(self, context))) {
        return CPyAttr_UndefinedError(self, context);
    }
    return PyLong_FromLong(value);
}

PyObject *CPyAttr_GetterInt64(PyObject *self, CPyAttr_Context *context) {
    int64_t value = *(int64_t *)((char *)self + context->offset);
    if (unlikely(value == CPY_LL_INT_ERROR
            && !context->always_defined
            && is_undefined_via_bitmap(self, context))) {
        return CPyAttr_UndefinedError(self, context);
    }
    return PyLong_FromLongLong(value);
}

int CPyAttr_SetterPyObject(PyObject *self, PyObject *value, CPyAttr_Context *context) {
    if (value == NULL && !context->deletable) {
        return CPyAttr_UndeletableError(self, context);
    }

    PyObject **attr = (PyObject **)((char *)self + context->offset);
    if (value != NULL) {
        PyTypeObject *type = NULL;
        switch (context->boxed_setter.type) {
            case CPyAttr_UNICODE:
                type = &PyUnicode_Type;
                break;
            case CPyAttr_LONG:
                type = &PyLong_Type;
                break;
            case CPyAttr_BOOL:
                type = &PyBool_Type;
                break;
            case CPyAttr_FLOAT:
                type = &PyFloat_Type;
                break;
            case CPyAttr_TUPLE:
                type = &PyTuple_Type;
                break;
            case CPyAttr_LIST:
                type = &PyList_Type;
                break;
            case CPyAttr_DICT:
                type = &PyDict_Type;
                break;
            case CPyAttr_SET:
                type = &PySet_Type;
                break;
            case CPyAttr_ANY:
                // Do nothing, type is already NULL.
                break;
        }
        if (unlikely(type != NULL && !PyObject_TypeCheck(value, type))) {
            if (!context->boxed_setter.optional || value != Py_None) {
                CPy_TypeError(context->boxed_setter.type_name, value);
                return -1;
            }
        }
        Py_XSETREF(*attr, Py_NewRef(value));
    } else {
        Py_CLEAR(*attr);
    }
    return 0;
}

int CPyAttr_SetterTagged(PyObject *self, PyObject *value, CPyAttr_Context *context) {
    if (value == NULL && !context->deletable) {
        return CPyAttr_UndeletableError(self, context);
    }

    CPyTagged *attr = (CPyTagged *)((char *)self + context->offset);
    if (value != NULL) {
        if (unlikely(!PyLong_Check(value))) {
            CPy_TypeError("int", value);
            return -1;
        }
        if (*attr != CPY_INT_TAG) {
            CPyTagged_DECREF(*attr);
        }
        *attr = CPyTagged_FromObject(value);
    } else {
        if (*attr != CPY_INT_TAG) {
            CPyTagged_DECREF(*attr);
        }
        *attr = CPY_INT_TAG;
    }
    return 0;
}

int CPyAttr_SetterBool(PyObject *self, PyObject *value, CPyAttr_Context *context) {
    if (value == NULL && !context->deletable) {
        return CPyAttr_UndeletableError(self, context);
    }

    char *attr = (char *)self + context->offset;
    if (value != NULL) {
        if (unlikely(!PyBool_Check(value))) {
            CPy_TypeError("bool", value);
            return -1;
        }
        *attr = value == Py_True;
    } else {
        *attr = 2;
    }
    return 0;
}

int CPyAttr_SetterFloat(PyObject *self, PyObject *value, CPyAttr_Context *context) {
    if (value == NULL && !context->deletable) {
        return CPyAttr_UndeletableError(self, context);
    }

    double *attr = (double *)((char *)self + context->offset);
    if (value != NULL) {
        if (unlikely(!PyFloat_Check(value))) {
            CPy_TypeError("float", value);
            return -1;
        }
        double tmp = PyFloat_AsDouble(value);
        if (unlikely(tmp == -1.0 && PyErr_Occurred())) {
            return -1;
        }
        *attr = tmp;
        if (tmp == CPY_FLOAT_ERROR) {
            set_definedness_in_bitmap(self, context, true);
        }
    } else {
        *attr = CPY_FLOAT_ERROR;
        set_definedness_in_bitmap(self, context, false);
    }
    return 0;
}

int CPyAttr_SetterInt16(PyObject *self, PyObject *value, CPyAttr_Context *context) {
    if (value == NULL && !context->deletable) {
        return CPyAttr_UndeletableError(self, context);
    }

    int16_t *attr = (int16_t *)((char *)self + context->offset);
    if (value != NULL) {
        if (unlikely(!PyLong_Check(value))) {
            CPy_TypeError("int16", value);
            return -1;
        }
        int16_t tmp = CPyLong_AsInt16(value);
        if (unlikely(tmp == CPY_LL_INT_ERROR && PyErr_Occurred())) {
            return -1;
        }
        *attr = tmp;
        if (tmp == CPY_LL_INT_ERROR) {
            set_definedness_in_bitmap(self, context, true);
        }
    } else {
        *attr = CPY_LL_INT_ERROR;
        set_definedness_in_bitmap(self, context, false);
    }
    return 0;
}

int CPyAttr_SetterInt32(PyObject *self, PyObject *value, CPyAttr_Context *context) {
    if (value == NULL && !context->deletable) {
        return CPyAttr_UndeletableError(self, context);
    }

    int32_t *attr = (int32_t *)((char *)self + context->offset);
    if (value != NULL) {
        if (unlikely(!PyLong_Check(value))) {
            CPy_TypeError("int32", value);
            return -1;
        }
        int32_t tmp = CPyLong_AsInt32(value);
        if (unlikely(tmp == CPY_LL_INT_ERROR && PyErr_Occurred())) {
            return -1;
        }
        *attr = tmp;
        if (tmp == CPY_LL_INT_ERROR) {
            set_definedness_in_bitmap(self, context, true);
        }
    } else {
        *attr = CPY_LL_INT_ERROR;
        set_definedness_in_bitmap(self, context, false);
    }
    return 0;
}

int CPyAttr_SetterInt64(PyObject *self, PyObject *value, CPyAttr_Context *context) {
    if (value == NULL && !context->deletable) {
        return CPyAttr_UndeletableError(self, context);
    }

    int64_t *attr = (int64_t *)((char *)self + context->offset);
    if (value != NULL) {
        if (unlikely(!PyLong_Check(value))) {
            CPy_TypeError("int64", value);
            return -1;
        }
        int64_t tmp = CPyLong_AsInt64(value);
        if (unlikely(tmp == CPY_LL_INT_ERROR && PyErr_Occurred())) {
            return -1;
        }
        *attr = tmp;
        if (tmp == CPY_LL_INT_ERROR) {
            set_definedness_in_bitmap(self, context, true);
        }
    } else {
        *attr = CPY_LL_INT_ERROR;
        set_definedness_in_bitmap(self, context, false);
    }
    return 0;
}
