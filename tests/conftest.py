from mesh import Mesh
from pytest import fixture


@fixture
def mesh():
    return Mesh()
