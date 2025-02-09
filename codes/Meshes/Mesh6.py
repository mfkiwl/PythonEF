import Display
from Interface_Gmsh import Interface_Gmsh, ElemType
from Geom import Point, Line, Circle, PointsList, Domain, Contour
import Materials
import Simulations

if __name__ == '__main__':

    Display.Clear()

    L = 1
    meshSize = L/4

    contour = Domain(Point(), Point(L, L), meshSize)
    circle = Circle(Point(L/2,L/2), L/3, meshSize)
    inclusions = [circle]

    refine1 = Domain(Point(0, L), Point(L, L*0.8), meshSize/8)
    refine2 = Circle(circle.center, L/2, meshSize/8)
    refine3 = Circle(Point(), L/2, meshSize/8)
    refineGeoms = [refine1, refine2, refine3]


    def DoMesh(dim, elemType):
        if dim == 2:
            mesh = Interface_Gmsh().Mesh_2D(contour, inclusions, elemType, refineGeoms=refineGeoms)
        elif dim == 3:
            mesh = Interface_Gmsh().Mesh_3D(contour, inclusions, [0, 0, -L], [3], elemType, refineGeoms=refineGeoms)

        Display.Plot_Mesh(mesh)

    [DoMesh(2, elemType) for elemType in ElemType.get_2D()]

    [DoMesh(3, elemType) for elemType in ElemType.get_3D()]

    geoms = [contour, circle, refine1, refine2, refine3]
    contour.Plot_Geoms(geoms)

    Display.plt.show()