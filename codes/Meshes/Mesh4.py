
import Display
from Interface_Gmsh import Interface_Gmsh, ElemType
from Geom import Point, PointsList, Circle, Line
import numpy as np

if __name__ == '__main__':

    Display.Clear()

    width = 1
    height = 2
    radius = 1

    meshSize = width/5

    pt1 = Point(radius, 0, r=width/3)
    pt2 = Point(radius+width, 0, r=width/3)
    pt3 = Point(radius+width, height, r=-width/3)
    pt4 = Point(radius, height, r=-width/3)

    contour = PointsList([pt1, pt2, pt3, pt4], meshSize)

    circle1 = Circle(Point(width/2+radius, height*1/4), width/3, width/10)
    circle2 = Circle(Point(width/2+radius, height*3/4), width/3, width/10)
    circle3 = Circle(Point(width/2+radius, height/2), width/3, width/10, False)
    inclusions = [circle1, circle2, circle3]

    axis = Line(Point(), Point(radius/3,height))
    axis.name = 'rot axis'

    angle = np.pi * 2 * 4/6

    perimeter = angle * radius

    layers = [perimeter // meshSize]

    def DoMesh(dim, elemType):
        mesh = Interface_Gmsh().Mesh_Revolve(contour, inclusions, axis, angle, layers, elemType)
        Display.Plot_Mesh(mesh)

    [DoMesh(3, elemType) for elemType in ElemType.get_3D()]

    geoms = [contour.Get_Contour()]
    geoms.extend([circle1, circle2, circle3])
    geoms.append(axis)
    contour.Plot_Geoms(geoms)

    Display.plt.show()