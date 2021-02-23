#!/bin/bash

set -e
set -x

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null && pwd )"

export LC_ALL=C
export TEST_MYPYC=1
export MYPY_USE_MYPYC=1
export MYPYC_OPT_LEVEL=0
export MYPY_TEST_PREFIX=${DIR}  # not good, should be part of the mypy module,
                                # like the mypyc test data is part of the mypyc module

package=mypy
module=mypy
module2=mypyc
slug=${TRAVIS_PULL_REQUEST_SLUG:=python/mypy}
repo=https://github.com/${slug}.git
run_tests() {  # synchronize with pytest.ini
	py.test -o testpaths=${module}/test \
	-o python_files=test*.py -o python_classes= \
	-o python_functions= -nauto --pyargs ${module}
	py.test -o testpaths=${module2}/test \
	-o python_files=test*.py -o python_classes= \
	-o python_functions= -k 'not test_c_unit_test and not testCoberturaParser' -nauto --pyargs ${module2}

}
pipver=10.0.0  # minimum required version of pip given python3.6+ and --no-build-isolation
setuptoolsver=24.2.0 # required to generate correct metadata for
                     # python_requires

rm -Rf testenv? || /bin/true

export HEAD=${TRAVIS_PULL_REQUEST_SHA:-$(git rev-parse HEAD)}

if [ "${RELEASE_SKIP}" != "head" ]
then
	testenv1=$(mktemp -d -t "${package}_env1-XXXXXXXXXX")
	virtualenv "${testenv1}" -p python3
	# First we test the head
	# shellcheck source=/dev/null
	source "${testenv1}/bin/activate"
	rm -Rf "${testenv1}/local"
	rm -f "${testenv1}/lib/python-wheels/setuptools"* \
		&& pip install --force-reinstall -U pip==${pipver} \
	        && pip install setuptools==${setuptoolsver} wheel
	pip install -rmypy-requirements.txt
	pip install -rtest-requirements.txt
	python setup.py build_ext --inplace
	./runtests.py
	pip uninstall -y ${package} || true; pip install --no-build-isolation .
	post_install1_test=$(mktemp -d -t ${package}_env1_test-XXXXXXXXXX)
	# if there is a subdir named '${module}' py.test will execute tests
	# there instead of the installed module's tests
	pushd "${post_install1_test}"
	# shellcheck disable=SC2086
	run_tests; popd
fi

testenv2=$(mktemp -d -t ${package}_env2-XXXXXXXXXX)
testenv3=$(mktemp -d -t ${package}_env3-XXXXXXXXXX)

virtualenv "${testenv2}" -p python3
virtualenv "${testenv3}" -p python3
rm -Rf "${testenv2}/local" "${testenv3}/local"

# Secondly we test via pip

cd "${testenv2}"
# shellcheck source=/dev/null
source bin/activate
rm -f lib/python-wheels/setuptools* \
	&& pip install --force-reinstall -U pip==${pipver} \
        && pip install setuptools==${setuptoolsver} wheel typing_extensions mypy_extensions typed_ast
pip install --no-build-isolation -e "git+${repo}@${HEAD}#egg=${package}"
cd src/${package}
pip install -rmypy-requirements.txt
pip install -rtest-requirements.txt
python setup.py sdist bdist_wheel
./runtests.py
cp dist/${package}*tar.gz "${testenv3}/"
pip uninstall -y ${package} || true; pip install --no-build-isolation .
post_install2_test=$(mktemp -d -t "${package}_env2_test-XXXXXXXXXX")
cd "${post_install2_test}" # no subdir named ${package} here, safe for py.testing the installed module
# shellcheck disable=SC2086
run_tests

# Is the distribution in testenv2 complete enough to build another
# functional distribution?

cd "${testenv3}"
# shellcheck source=/dev/null
source bin/activate
rm -f lib/python-wheels/setuptools* \
	&& pip install --force-reinstall -U pip==${pipver} \
        && pip install setuptools==${setuptoolsver} wheel
pip install "-r${DIR}/mypy-requirements.txt"
pip install "-r${DIR}/test-requirements.txt"
mkdir out
tar --extract --directory=out -z -f ${package}*.tar.gz
cd out/${package}*
python setup.py build_ext --inplace
./runtests.py
pip uninstall -y ${package} || true; pip install --no-build-isolation .
post_install3_test=$(mktemp -d -t "${package}_env3_test-XXXXXXXXXX")
pushd "${post_install3_test}"
# shellcheck disable=SC2086
run_tests; popd
