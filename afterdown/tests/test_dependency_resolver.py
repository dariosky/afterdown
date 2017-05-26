import pytest

from afterdown.core.utils import dependency_resolver, CircularDependencyException


def test_dependency():
    objects = [
        dict(name='a', depends_on=['b', 'c']),
        dict(name='b', depends_on=['c']),
        dict(name='c'),
        dict(name='d', depends_on=['c', 'b']),
    ]

    order = []
    process_func = lambda x: order.append(x['name'])
    get_dependencies_func = lambda child: filter(
        lambda par: par['name'] in child.get('depends_on', ''), objects
    )
    dependency_resolver(objects, get_dependencies_func, process_func)
    assert order == ['c', 'b', 'a', 'd'] or order == ['c', 'b', 'd', 'a']


def test_circular_dependency():
    objects = [
        dict(name='a', depends_on=['b', 'c']),
        dict(name='b', depends_on=['c']),
        dict(name='c', depends_on=['b'])
    ]

    order = []
    process_func = lambda x: order.append(x['name'])
    get_dependencies_func = lambda child: filter(
        lambda par: par['name'] in child.get('depends_on', ''), objects
    )
    with pytest.raises(CircularDependencyException):
        dependency_resolver(objects, get_dependencies_func, process_func)
