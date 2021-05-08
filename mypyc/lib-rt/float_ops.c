// Floater point primitive operations

#include <Python.h>

#include "CPy.h"


PyObject PyFloat_Add(float left, float right ){

    if(likely(PyFloat_Check(left) && PyFloat_Check(right))) {

        PyObject sum = left + right;

    }

    return sum;
}