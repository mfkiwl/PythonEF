import Display
from Interface_Gmsh import Interface_Gmsh, ElemType
from Geom import Point, Line, Circle, PointsList, Domain

if __name__ == '__main__':

    Display.Clear()

    L = 120
    h = L * 0.3
    N = 4

    pt1 = Point(isOpen=True, r=-10)
    pt2 = Point(x=L)
    pt3 = Point(x=L, y=h)
    pt4 = Point(x=h, y=h, r=10)
    pt5 = Point(x=h, y=L)
    pt6 = Point(y=L)
    pt7 = Point(x=h, y=h)

    contour = PointsList([pt1, pt2, pt3, pt4, pt5, pt6], h / N)
    inclusions = [Circle(Point(x=h / 2, y=h * (i + 1)), h / 4, meshSize=h / N, isHollow=True) for i in range(3)]
    inclusions.extend([Domain(Point(x=h, y=h / 2 - h * 0.1), Point(x=h * 2.1, y=h / 2 + h * 0.1), isHollow=False, meshSize=h / N)])

    def DoMesh(dim, elemType):
        if dim == 2:
            mesh = Interface_Gmsh().Mesh_2D(contour, inclusions, elemType)
        elif dim == 3:
            mesh = Interface_Gmsh().Mesh_3D(contour, inclusions, [0, 0, -h], [3], elemType=elemType)

        Display.Plot_Mesh(mesh)

    [DoMesh(2, elemType) for elemType in ElemType.get_2D()]

    [DoMesh(3, elemType) for elemType in ElemType.get_3D()]

    geoms = [contour.Get_Contour()]; geoms.extend(inclusions)
    contour.Plot_Geoms(geoms)

    Display.plt.show()