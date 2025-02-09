"""Module for creating geometric objects."""

from typing import Union
import numpy as np
import copy

from numpy import ndarray
from scipy.optimize import minimize
import Display
from abc import ABC, abstractmethod

class Point:

    def __init__(self, x=0.0, y=0.0, z=0.0, isOpen=False, r=0.0):
        """Build a point.

        Parameters
        ----------
        x : float, optional
            x coordinate, default 0.0
        y : float, optional
            y coordinate, default 0.0
        z : float, optional
            z coordinate, default 0.0
        isOpen : bool, optional
            point can open (openCrack), default False
        r : float, optional
            radius used for fillet
        """
        self.__r = r
        self.__coordo = np.array([x, y, z], dtype=float)
        self.__isOpen = isOpen

    @property
    def x(self) -> float:
        """x coordinate"""
        return self.__coordo[0]

    @property
    def y(self) -> float:
        """y coordinate"""
        return self.__coordo[1]

    @property
    def z(self) -> float:
        """z coordinate"""
        return self.__coordo[2]

    @property
    def r(self) -> float:
        """radius used for fillet"""
        return self.__r

    @property
    def coordo(self) -> np.ndarray:
        """[x,y,z] coordinates"""
        return self.__coordo
    
    @coordo.setter
    def coordo(self, value) -> None:
        coord = self._getCoord(value)
        self.__coordo = coord

    @property
    def isOpen(self) -> bool:
        """point is open"""
        return self.__isOpen
    
    def Check(self, coord) -> bool:
        """Check if coordinates are identical"""
        coord = self._getCoord(coord)
        n = np.linalg.norm(self.coordo)
        n = 1 if n == 0 else n
        diff = np.linalg.norm(self.coordo - coord)/n
        return diff <= 1e-12
    
    @staticmethod
    def _getCoord(value) -> np.ndarray:
        if isinstance(value, Point):
            coordo = value.coordo        
        elif isinstance(value, (list, tuple, np.ndarray)):
            coordo = np.zeros(3)
            val = np.asarray(value, dtype=float)
            assert val.size <= 3, 'must not exceed size 3'
            coordo[:val.size] = val
        elif isinstance(value, (float, int)):            
            coordo = np.asarray([value]*3)
        else:
            raise Exception(f'{type(value)} is not supported. Must be (Point | float, int list | tuple | dict | set | np.ndarray)')
        
        return coordo
    
    def translate(self, dx: float=0.0, dy: float=0.0, dz: float=0.0) -> None:
        """translate the point"""
        self.__coordo = Translate_coordo(self.__coordo, dx, dy, dz).reshape(-1)

    def rotate(self, theta: float, center: tuple=(0,0,0), direction: tuple=(0,0,1)) -> None:
        """Rotate the point with around an axis.

        Parameters
        ----------
        theta : float
            rotation angle [rad] 
        center : tuple, optional
            rotation center, by default (0,0,0)
        direction : tuple, optional
            rotation direction, by default (0,0,1)
        """
        self.__coordo = Rotate_coordo(self.__coordo, theta, center, direction).reshape(-1)

    def symmetry(self, point=(0,0,0), n=(1,0,0)) -> None:
        """Symmetrise the point coordinates with a plane.

        Parameters
        ----------
        point : tuple, optional
            a point belonging to the plane, by default (0,0,0)
        n : tuple, optional
            normal to the plane, by default (1,0,0)
        """
        self.__coordo = Symmetry_coordo(self.__coordo, point, n).reshape(-1)
    
    def __radd__(self, value):
        return self.__add__(value)

    def __add__(self, value):
        coordo = self._getCoord(value)        
        newCoordo: np.ndarray = self.coordo + coordo
        return Point(*newCoordo, self.isOpen, self.r)

    def __rsub__(self, value):
        return self.__add__(value)
    
    def __sub__(self, value):
        coordo = self._getCoord(value)        
        newCoordo: np.ndarray = self.coordo - coordo
        return Point(*newCoordo, self.isOpen, self.r)
    
    def __rmul__(self, value):
        return self.__mul__(value)

    def __mul__(self, value):
        coordo = self._getCoord(value)
        newCoordo: np.ndarray = self.coordo * coordo
        return Point(*newCoordo, self.isOpen, self.r)
    
    def __rtruediv__(self, value):
        return self.__truediv__(value)

    def __truediv__(self, value):
        coordo = self._getCoord(value)
        newCoordo: np.ndarray = self.coordo / coordo
        return Point(*newCoordo, self.isOpen, self.r)
    
    def __rfloordiv__(self, value):
        return self.__floordiv__(value)

    def __floordiv__(self, value):
        coordo = self._getCoord(value)
        newCoordo: np.ndarray = self.coordo // coordo
        return Point(*newCoordo, self.isOpen, self.r)
    
    def copy(self):
        return copy.deepcopy(self)


class Geom(ABC):

    def __init__(self, points: list[Point], meshSize: float, name: str, isHollow: bool, isOpen: bool):
        """Builds a geometric object.

        Parameters
        ----------
        points : list[Point]
            list of points to build the geometric object
        meshSize : float
            mesh size that will be used to create the mesh >= 0
        name : str
            object name
        isHollow : bool
            Indicates whether the the formed domain is hollow/empty
        isOpen : bool
            Indicates whether the object can open to represent an open crack (openCrack)
        """
        assert meshSize >= 0
        self.__meshSize: float = meshSize
        self.__points: list[Point] = points
        self.__name: str = name
        self.__isHollow: bool = isHollow
        self.__isOpen: bool = isOpen

    @property
    def meshSize(self) -> float:
        """Element size used for meshing"""
        return self.__meshSize

    @property
    def points(self) -> list[Point]:
        """Points used to build the object"""
        return self.__points
    
    @property
    def coordo(self) -> np.ndarray:
        return np.asarray([p.coordo for p in self.points])
    
    @abstractmethod
    def coordoPlot(self) -> tuple[np.ndarray,np.ndarray]:
        """returns coordinates for constructing lines and points"""
        lines = self.coordo
        points = lines[[0,-1]]
        return lines, points    
    
    def copy(self):
        new = copy.deepcopy(self)
        new.name = new.name +'_copy'        
        return new

    @property
    def name(self) -> str:
        """object name"""
        return self.__name
    
    @name.setter
    def name(self, val: str) -> None:
        self.__name = val
    
    @property
    def isHollow(self) -> bool:
        """Indicates whether the the formed domain is hollow/empty"""
        return self.__isHollow
    
    @property
    def isOpen(self) -> bool:
        """Indicates whether the object can open to represent an open crack"""
        return self.__isOpen
    
    def translate(self, dx: float=0.0, dy: float=0.0, dz: float=0.0) -> None:
        """translate the object"""
        # to translate an object, all you have to do is move these points
        [p.translate(dx,dy,dz) for p in self.__points]
    
    def rotate(self, theta: float, center: tuple=(0,0,0), direction: tuple=(0,0,1)) -> None:        
        """Rotate the object coordinates around an axis.

        Parameters
        ----------        
        theta : float
            rotation angle [rad] 
        center : tuple, optional
            rotation center, by default (0,0,0)
        direction : tuple, optional
            rotation direction, by default (0,0,1)
        """
        oldCoord = self.coordo        
        newCoord = Rotate_coordo(oldCoord, theta, center, direction)

        dec = newCoord - oldCoord
        [point.translate(*dec[p]) for p, point in enumerate(self.points)]

    def symmetry(self, point=(0,0,0), n=(1,0,0)) -> None:
        """Symmetrise the object coordinates with a plane.

        Parameters
        ----------
        point : tuple, optional
            a point belonging to the plane, by default (0,0,0)
        n : tuple, optional
            normal to the plane, by default (1,0,0)
        """

        oldCoord = self.coordo
        newCoord = Symmetry_coordo(oldCoord, point, n)

        dec = newCoord - oldCoord
        [point.translate(*dec[p]) for p, point in enumerate(self.points)]


    def Plot(self, ax: Display.plt.Axes=None, color:str="", name:str="", plotPoints=True) -> Display.plt.Axes:

        if ax is None:
            fig, ax = Display.plt.subplots(subplot_kw=dict(projection='3d'))
            ax.set_xlabel('x')
            ax.set_ylabel('y')
            ax.set_zlabel('z')
            ax.view_init(elev=105, azim=-90)
            inDim = 3
        else:
            if ax.name == '3d':
                inDim = 3
            else:
                inDim = 2

        lines, points = self.coordoPlot()
        if color != "":
            ax.plot(*lines[:,:inDim].T, color=color, label=self.name)
        else:
            ax.plot(*lines[:,:inDim].T, label=self.name)
        if plotPoints:
            ax.plot(*points[:,:inDim].T, ls='', marker='.',c='black')

        if inDim == 3:
            xlim, ylim, zlim = ax.get_xlim(), ax.get_ylim(), ax.get_zlim()
            oldBounds = np.array([xlim, ylim, zlim]).T
            lines = np.concatenate((lines, oldBounds), 0)
            Display._Axis_equal_3D(ax, lines)

        return ax
    
    @staticmethod
    def Plot_Geoms(geoms: list, ax: Display.plt.Axes=None,
                   color:str="", name:str="", plotPoints=True) -> Display.plt.Axes:
        geoms: list[Geom] = geoms
        for g, geom in enumerate(geoms):
            if g == 0 and ax == None:
                ax = geom.Plot(color=color, name=name, plotPoints=plotPoints)
            else:
                geom.Plot(ax, color, name, plotPoints=plotPoints)

        ax.legend()

        return ax

class PointsList(Geom):

    __nbPointsList = 0

    def __init__(self, points: list[Point], meshSize=0.0, isHollow=True, isOpen=False):
        """Builds a point list. Can be used to construct a closed surface or a spline.

        Parameters
        ----------
        points : list[Point]
            list of points
        meshSize : float, optional
            mesh size that will be used to create the mesh >= 0, by default 0.0
        isHollow : bool, optional
            the formed domain is hollow/empty, by default True
        isOpen : bool, optional
            the spline formed by the points list can be opened (openCrack), by default False
        """

        assert len(points) > 1

        self.pt1 = points[0]
        """First point"""
        self.pt2 = points[-1]
        """Last point"""

        PointsList.__nbPointsList += 1
        name = f"PointsList{PointsList.__nbPointsList}"
        super().__init__(points, meshSize, name, isHollow, isOpen)

    def Get_Contour(self):
        """Builds a contour from the point list.\n
        Pass a fillet if a point has a radius which is not 0."""

        coordinates = self.coordo
        N = coordinates.shape[0]
        mS = self.meshSize

        # TODO Permettre d'ajouter des congés ?

        # Get corners
        corners: list[Geom] = []
        geoms: list[Geom] = []


        def Link(idx1: int, idx2: int):
            # this function make the link between corners[idx1] and corners[idx2]
            
            # get the last point associated with idx1
            if isinstance(corners[idx1], Point):
                p1 = corners[idx1]
            else:
                # get the last coordinates
                p1 = corners[idx1].points[-1]

            # get the first point associated with idx2
            if isinstance(corners[idx2], Point):
                p2 = corners[idx2]
            else:
                # get the first coordinates
                p2 = corners[idx2].points[0]                
            
            if not p1.Check(p2):
                line = Line(p1, p2, mS, self.isOpen)
                geoms.append(line)

            if isinstance(corners[-1], (CircleArc, Line)) and idx2 != 0:
                geoms.append(corners[-1])

        for p, point in enumerate(self.points):

            prev = p-1
            next = p+1 if p+1 < N else 0

            isOpen = point.isOpen

            if point.r == 0:

                corners.append(point)

            else:
                A, B, C = Points_Rayon(point.coordo, coordinates[prev], coordinates[next], point.r)

                pA = Point(*A, isOpen)
                pB = Point(*B, isOpen)
                pC = Point(*C, isOpen)

                corners.append(CircleArc(pA, pB, pC, meshSize=mS))
            
            if p > 0:
                Link(-2, -1)
            elif isinstance(corners[-1], (CircleArc, Line)):
                geoms.append(corners[-1])
                
        Link(-1, 0)

        contour = Contour(geoms, self.isHollow, self.isOpen).copy()
        contour.name = self.name + '_contour'
        # do the copy to unlink the points connexion with the list of points
        
        return contour

    def coordoPlot(self) -> tuple[np.ndarray,np.ndarray]:
        return super().coordoPlot()
    
    @property
    def length(self) -> float:
        coordo = self.coordo
        lenght = np.linalg.norm(coordo[1:]-coordo[:-1], axis=1)
        lenght = np.sum(lenght)
        return lenght

class Line(Geom):

    __nbLine = 0

    @staticmethod
    def distance(pt1: Point, pt2: Point) -> float:
        """Calculate the distance between two points."""
        length = np.sqrt((pt1.x-pt2.x)**2 + (pt1.y-pt2.y)**2 + (pt1.z-pt2.z)**2)
        return np.abs(length)
    
    @staticmethod
    def get_unitVector(pt1: Point, pt2: Point) -> np.ndarray:
        """Construct the unit vector between two points."""
        length = Line.distance(pt1, pt2)        
        v = np.array([pt2.x-pt1.x, pt2.y-pt1.y, pt2.z-pt1.z])/length
        return v   

    def __init__(self, pt1: Point, pt2: Point, meshSize=0.0, isOpen=False):
        """Builds a line.

        Parameters
        ----------
        pt1 : Point
            first point
        pt2 : Point
            second point
        meshSize : float, optional
            mesh size that will be used to create the mesh >= 0, by default 0.0
        isOpen : bool, optional
            line can be opened (openCrack), by default False
        """
        self.pt1 = pt1
        self.pt2 = pt2

        Line.__nbLine += 1
        name = f"Line{Line.__nbLine}"
        Geom.__init__(self, [pt1, pt2], meshSize, name, False, isOpen)
    
    @property
    def unitVector(self) -> np.ndarray:
        """The unit vector for the two points on the line (p2-p1)"""
        return Line.get_unitVector(self.pt1, self.pt2)

    @property
    def length(self) -> float:
        """Calculate the distance between the two points on the line"""
        return Line.distance(self.pt1, self.pt2)
    
    def coordoPlot(self) -> tuple[np.ndarray,np.ndarray]:
        return super().coordoPlot()

class Domain(Geom):

    __nbDomain = 0

    def __init__(self, pt1: Point, pt2: Point, meshSize=0.0, isHollow=True):
        """Builds a domain

        Parameters
        ----------
        pt1 : Point
            first point
        pt2 : Point
            second point
        meshSize : float, optional
            mesh size that will be used to create the mesh >= 0, by default 0.0
        isHollow : bool, optional
            the formed domain is hollow/empty, by default True
        """
        self.pt1 = pt1
        self.pt2 = pt2

        Domain.__nbDomain += 1
        name = f"Domain{Domain.__nbDomain}"
        # a domain can't be open
        Geom.__init__(self, [pt1, pt2], meshSize, name, isHollow, False)

    def coordoPlot(self) -> tuple[np.ndarray,np.ndarray]:

        p1 = self.pt1.coordo
        p7 = self.pt2.coordo

        dx, dy, dz = p7 - p1

        p2 = p1 + [dx,0,0]
        p3 = p1 + [dx,dy,0]
        p4 = p1 + [0,dy,0]
        p5 = p1 + [0,0,dz]
        p6 = p1 + [dx,0,dz]
        p8 = p1 + [0,dy,dz]

        lines = np.concatenate((p1,p2,p3,p4,p1,p5,p6,p2,p6,p7,p3,p7,p8,p4,p8,p5)).reshape((-1,3))

        points = np.concatenate((p1,p7)).reshape((-1,3))

        return lines, points

class Circle(Geom):

    __nbCircle = 0

    def __init__(self, center: Point, diam: float, meshSize=0.0, isHollow=True, isOpen=False, n=(0,0,1)):
        """Constructing a circle according to its center, diameter and the normal vector

        Parameters
        ----------
        center : Point
            center of circle
        diam : float
            diameter
        meshSize : float, optional
            mesh size that will be used to create the mesh >= 0, by default 0.0
        isHollow : bool, optional
            circle is hollow/empty, by default True
        isOpen : bool, optional
            circle can be opened (openCrack), by default False
        n : tuple, optional
            normal direction to the circle, by default (0,0,1)
        """
        
        assert diam > 0.0        

        r = diam/2        

        # creates points associated with the circle
        self.center = center
        self.pt1 = center + [r, 0, 0]
        self.pt2 = center + [0, r, 0]
        self.pt3 = center + [-r, 0, 0]
        self.pt4 = center + [0, -r, 0]
        # creates circle arcs associated with the circle
        circleArc1 = CircleArc(self.pt1, self.pt2, center=center, meshSize=meshSize, isOpen=isOpen)
        circleArc2 = CircleArc(self.pt2, self.pt3, center=center, meshSize=meshSize, isOpen=isOpen)
        circleArc3 = CircleArc(self.pt3, self.pt4, center=center, meshSize=meshSize, isOpen=isOpen)
        circleArc4 = CircleArc(self.pt4, self.pt1, center=center, meshSize=meshSize, isOpen=isOpen)
        # create the contour object associated with the circle
        self.contour = Contour([circleArc1, circleArc2, circleArc3, circleArc4], isHollow, isOpen)

        Circle.__nbCircle += 1
        name = f"Circle{Circle.__nbCircle}"
        Geom.__init__(self, [center, self.pt1, self.pt2, self.pt3, self.pt4], meshSize, name, isHollow, isOpen)

        # rotatate if necessary
        zAxis = np.array([0,0,1])
        n = normalize_vect(Point._getCoord(n))
        rotAxis = np.cross(n, zAxis)
        # theta = AngleBetween_a_b(zAxis, n)
        
        # then we rotate along i
        if np.linalg.norm(rotAxis) == 0:
            # n and zAxis are collinear
            i = normalize_vect((self.pt1 - center).coordo) # i = p1 - center
        else:
            i = rotAxis

        mat = JacobianMatrix(i,n)

        coordo = np.einsum('ij,nj->ni', mat, self.coordo - center.coordo) + center.coordo

        for p, point in enumerate(self.points):
            point.coordo = coordo[p]

    @property
    def diam(self) -> float:
        """circle diameter"""
        p1 = self.pt1.coordo
        pC = self.center.coordo
        return np.linalg.norm(p1-pC) * 2

    @property
    def n(self) -> np.ndarray:
        """axis normal to the circle"""
        i = normalize_vect((self.pt1 - self.center).coordo)
        j = normalize_vect((self.pt2 - self.center).coordo)
        n: np.ndarray = normalize_vect(np.cross(i,j))
        return n

    def coordoPlot(self) -> tuple[np.ndarray,np.ndarray]:        

        angle = np.linspace(0, np.pi*2, 40)

        pC = self.center
        R = self.diam/2

        points = self.coordo
        
        lines = np.zeros((angle.size, 3))
        lines[:,0] = np.cos(angle)*R
        lines[:,1] = np.sin(angle)*R
        
        # construct jacobian matrix
        i = (self.pt1 - self.center).coordo
        n = self.n
        mat = JacobianMatrix(i, n)

        # change base
        lines = np.einsum('ij,nj->ni', mat, lines) + pC.coordo

        return lines, points[1:]
    
    @property
    def length(self) -> float:
        """circle perimeter"""
        return np.pi * self.diam

class CircleArc(Geom):

    __nbCircleArc = 0

    def __init__(self, pt1: Point, pt2: Point, center:Point=None, R:float=None, P:Point=None, meshSize=0.0, n=(0,0,1), isOpen=False, coef=1):
        """Construct a circular arc using several methods:
            1: with 2 points, a radius R and a normal vector n.
            2: with 2 points and a center
            3: with 2 points and a point P belonging to the circle\n
            The methods are chosen in the following order 3 2 1. This means that if you enter P, the other methods will not be used.

        Parameters
        ----------        
        pt1 : Point
            starting point
        pt2: Point
            ending point
        R: float, optional
            radius of the arc circle, by default None
        center: Point, optional
            center of circular arc, by default None
        P: Point, optional
            a point belonging to the circle, by default None
        meshSize : float, optional
            size to be used for mesh construction, by default 0.0
        n: np.ndarray | list | tuple, optional
            normal vector to the arc circle, by default (0,0,1)
        isOpen : bool, optional
            arc can be opened, by default False
        coef: int, optional
            Change direction, by default 1 or -1
        """

        # first check that pt1 and pt2 dont share the same coordinates
        assert not pt1.Check(pt2), 'pt1 and pt2 are on the same coordinates'        

        if P != None:
            center = Circle_Triangle(pt1, pt2, P)
            center = Point(*center)

        elif center != None:
            assert not pt1.Check(center), 'pt1 and center are on the same coordinates'            

        elif R != None:            
            coordo = np.array([pt1.coordo, pt2.coordo])
            center = Circle_Coordo(coordo, R, n)
            center = Point(*center)
            
        else:

            raise Exception('must give P, center or R')
        
        r1 = np.linalg.norm((pt1-center).coordo)
        r2 = np.linalg.norm((pt2-center).coordo)
        assert (r1 - r2)**2/r2**2 <= 1e-12, "The given center doesn't have the right coordinates. If the center coordinate is difficult to identify, you can give:\n - the radius R with the vector normal to the circle n\n - another point belonging to the circle."

        self.center = center
        """Point at the center of the arc."""
        self.pt1 = pt1
        """Starting point of the arc."""
        self.pt2 = pt2
        """Ending point of the arc."""

        # Here we'll create an intermediate point, because in gmsh, circular arcs are limited to an angle pi.

        i1 = (pt1-center).coordo
        i2 = (pt2-center).coordo

        collinear = np.linalg.norm(np.cross(i1, i2)) <= 1e-12

        # construction of the passage matrix
        k = np.array([0,0,1])
        if collinear:
            vect = normalize_vect(i2-i1)
            i = np.cross(k,vect)
        else:
            i = normalize_vect((i1+i2)/2)
            k = normalize_vect(np.cross(i1, i2))
        j = np.cross(k, i)

        mat = np.array([i,j,k]).T

        # midpoint coordinates
        assert coef in [-1, 1], 'coef must be in [-1, 1]'
        pt3 = center.coordo + mat @ [coef*r1,0,0]

        self.pt3 = Point(*pt3)
        """Midpoint of the circular arc."""

        CircleArc.__nbCircleArc += 1
        name = f"CircleArc{CircleArc.__nbCircleArc}"
        Geom.__init__(self, [pt1, center, self.pt3, pt2], meshSize, name, False, isOpen)

    @property
    def n(self) -> np.ndarray:
        """axis normal to the circle arc"""
        i = normalize_vect((self.pt1 - self.center).coordo)        
        if self.angle in [0, np.pi]:            
            j = normalize_vect((self.pt3 - self.center).coordo)
        else:
            j = normalize_vect((self.pt2 - self.center).coordo)
        n = normalize_vect(np.cross(i,j))
        return n
    
    @property
    def angle(self):
        """circular arc angle [rad]"""
        i = (self.pt1 - self.center).coordo
        j = (self.pt2 - self.center).coordo
        return AngleBetween_a_b(i,j)
    
    @property
    def r(self):
        """circular arc radius"""
        return np.linalg.norm((self.pt1-self.center).coordo)
    
    @property
    def length(self) -> float:
        """circular arc length"""
        return np.abs(self.angle * self.r)

    def coordoPlot(self) -> tuple[np.ndarray,np.ndarray]:

        points = self.coordo

        pC = self.center
        r = self.r

        # plot arc circle in 2D space
        angles = np.linspace(0, np.abs(self.angle), 11)
        lines = np.zeros((angles.size,3))
        lines[:,0] = np.cos(angles) * r
        lines[:,1] = np.sin(angles) * r

        # get the jabobian matrix
        i = (self.pt1 - self.center).coordo        
        n = self.n
        
        mat = JacobianMatrix(i,n)

        # transform coordinates
        lines = np.einsum('ij,nj->ni', mat, lines) + pC.coordo

        return lines, points[[0,-1]]

class Contour(Geom):

    __nbContour = 0

    def __init__(self, geoms: list[Union[Line,CircleArc,PointsList]], isHollow=True, isOpen=False):
        """Create a contour from a list of lines or arcs.

        Parameters
        ----------
        geoms : list[Line | CircleArc | PointsList]
            list of objects used to build the contour
        isHollow : bool, optional
            the formed domain is hollow/empty, by default True
        isOpen : bool, optional
            contour can be opened, by default False
        """

        # Check that the points form a closed loop
        points: list[Point] = []

        tol = 1e-12        

        for i, geom in enumerate(geoms):

            assert isinstance(geom, (Line, CircleArc, PointsList)), "Must give a list of lines and arcs or points."

            if i == 0:
                ecart = tol
            elif i > 0 and i < len(geoms)-1:
                # check that the starting point has the same coordinate as the last point of the previous object
                ecart = np.linalg.norm(geom.points[0].coordo - points[-1].coordo)

                assert ecart <= tol, "The contour must form a closed loop."
            else:
                # checks that the end point of the last geometric object is the first point created.
                ecart1 = np.linalg.norm(geom.points[0].coordo - points[-1].coordo)
                ecart2 = np.linalg.norm(geom.points[-1].coordo - points[0].coordo)

                assert ecart1 <= tol and ecart2 <= tol, "The contour must form a closed loop."

            # Adds the first and last points
            points.extend([p for p in geom.points if p not in points])

        self.geoms = geoms

        Contour.__nbContour += 1
        name = f"Contour{Contour.__nbContour}"
        meshSize = np.mean([geom.meshSize for geom in geoms])
        Geom.__init__(self, points, meshSize, name, isHollow, isOpen)

    def coordoPlot(self) -> tuple[np.ndarray,np.ndarray]:

        lines = []
        points = []

        for geom in self.geoms:
            l, p = geom.coordoPlot()
            lines.extend(l.reshape(-1))
            points.extend(p.reshape(-1))

        lines = np.reshape(lines, (-1,3))
        points = np.reshape(points, (-1,3))

        return lines, points
    
    @property
    def length(self) -> float:
        return np.sum([geom.length for geom in self.geoms])

# Functions for calculating distances, angles, etc.

def normalize_vect(vect: np.ndarray) -> np.ndarray:
    """Returns the normalized vector."""
    vect = np.asarray(vect)
    if len(vect.shape) == 1:
        return vect / np.linalg.norm(vect)
    elif len(vect.shape) == 2:
        return np.einsum('ij,i->ij',vect, 1/np.linalg.norm(vect, axis=1), optimize="optimal")
    else:
        raise Exception("The vector is the wrong size")

def rotation_matrix(vect: np.ndarray, theta: float) -> np.ndarray:
    """Gets the rotation matrix for turning along an axis with theta angle (rad).\n
    p(x,y) = matrice • p(i,j)\n
    https://en.wikipedia.org/wiki/Rotation_matrix#Axis_and_angle"""

    x, y, z = normalize_vect(vect)
    
    c = np.cos(theta)
    s = np.sin(theta)
    C = 1 - c
    mat = np.array([[x*x*C + c,   x*y*C - z*s, x*z*C + y*s],
                    [y*x*C + z*s, y*y*C + c,   y*z*C - x*s],
                    [z*x*C - y*s, z*y*C + x*s, z*z*C + c]])
    
    return mat


def AngleBetween_a_b(a: np.ndarray, b: np.ndarray) -> float:
    """Calculates the angle between vector a and vector b.
    https://math.stackexchange.com/questions/878785/how-to-find-an-angle-in-range0-360-between-2-vectors"""

    a = Point._getCoord(a)
    b = Point._getCoord(b)

    proj = normalize_vect(a) @ normalize_vect(b)    

    if np.abs(proj) == 1:
        # a and b are colinear
        angle = 0 if proj == 1 else np.pi

    else:    
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)        
        angle = np.arccos((a @ b)/(norm_a*norm_b))
    
    return angle

def Translate_coordo(coordo: np.ndarray, dx: float=0.0, dy: float=0.0, dz: float=0.0) -> np.ndarray:
    """Translate the coordinates."""

    oldCoordo = np.reshape(coordo, (-1, 3))

    dec = Point._getCoord([dx, dy, dz])

    newCoord = oldCoordo + dec

    return newCoord

def Rotate_coordo(coordo: np.ndarray, theta: float, center: tuple=(0,0,0), direction: tuple=(0,0,1)) -> np.ndarray:
    """Rotate the coordinates arround a specified center and axis.

    Parameters
    ----------
    coordo : np.ndarray
        coordinates to rotate (n,3)
    theta : float
        rotation angle [rad] 
    center : tuple, optional
        rotation center, by default (0,0,0)
    direction : tuple, optional
        rotation direction, by default (0,0,1)

    Returns
    -------
    np.ndarray
        rotated coordinates
    """

    center = Point._getCoord(center)
    direction = Point._getCoord(direction)

    # rotation matrix
    rotMat = rotation_matrix(direction, theta)

    oldCoordo = np.reshape(coordo, (-1,3))
    
    newCoord: np.ndarray = np.einsum('ij,nj->ni', rotMat, oldCoordo - center, optimize='optimal') + center

    return newCoord

def Symmetry_coordo(coordo: np.ndarray, point=(0,0,0), n=(1,0,0)) -> np.ndarray:
    """Symmetrise coordinates with a plane.

    Parameters
    ----------
    coordo : np.ndarray
        coordinates that we want to symmetrise
    point : tuple, optional
        a point belonging to the plane, by default (0,0,0)
    n : tuple, optional
        normal to the plane, by default (1,0,0)

    Returns
    -------
    np.ndarray
        the new coordinates
    """

    point = Point._getCoord(point)
    n = normalize_vect(Point._getCoord(n))

    oldCoordo = np.reshape(coordo, (-1,3))

    d = (oldCoordo - point) @ n    

    newCoord = oldCoordo - np.einsum('n,i->ni', 2*d, n, optimize='optimal')

    return newCoord

def JacobianMatrix(i: np.ndarray, k: np.ndarray) -> np.ndarray:
    """Compute the Jacobian matrix to transform local coordinates (i,j,k) to global (x,y,z) coordinates.\n
    p(x,y,z) = J • p(i,j,k) and p(i,j,k) = inv(J) • p(x,y,z)\n\n
    ix jx kx\n
    iy jy ky\n
    iz jz kz

    Parameters
    ----------
    i : np.ndarray
        i vector
    k : np.ndarray
        k vector
    """        

    i = normalize_vect(i)
    k = normalize_vect(k)
    
    j = np.cross(k, i)
    j = normalize_vect(j)

    F = np.zeros((3,3))

    F[:,0] = i
    F[:,1] = j
    F[:,2] = k

    return F

def Points_Rayon(P0: np.ndarray, P1: np.ndarray, P2: np.ndarray, r: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculation of point coordinates to create a radius in a corner.\n
    return A, B, C

    Parameters
    ----------
    P0 : np.ndarray
        coordinates of point with radius
    P1 : np.ndarray
        coordinates before P0 coordinates
    P2 : np.ndarray
        coordinates after P0 coordinates
    r : float
        radius at point P0

    Returns
    -------
    tuple[np.ndarray, np.ndarray, np.ndarray]
        coordinates calculated to construct the radius
    """
                
    # vectors
    i = P1-P0
    j = P2-P0
    
    n = np.cross(i, j) # normal vector to the plane formed by i, j

    if r > 0:
        # angle from i to k
        betha = AngleBetween_a_b(i, j)/2
        
        d = np.abs(r)/np.tan(betha) # distance between P0 and A on i and distance between P0 and B on j

        d *= np.sign(betha)

        A = JacobianMatrix(i, n) @ np.array([d,0,0]) + P0
        B = JacobianMatrix(j, n) @ np.array([d,0,0]) + P0
        C = JacobianMatrix(i, n) @ np.array([d,r,0]) + P0
    else:
        d = np.abs(r)
        A = JacobianMatrix(i, n) @ np.array([d,0,0]) + P0
        B = JacobianMatrix(j, n) @ np.array([d,0,0]) + P0
        C = P0

    return A, B, C

def Circle_Triangle(p1, p2, p3) -> np.ndarray:
    """Return center and radius for the circumcicular arc formed by 3 points.\n
    return center, R
    """

    # https://math.stackexchange.com/questions/1076177/3d-coordinates-of-circle-center-given-three-point-on-the-circle

    p1 = Point._getCoord(p1)
    p2 = Point._getCoord(p2)
    p3 = Point._getCoord(p3)

    v1 = p2-p1
    v2 = p3-p1

    v11 = v1 @ v1
    v22 = v2 @ v2
    v12 = v1 @ v2

    b = 1 / (2*(v11*v22-v12**2))
    k1 = b * v22 * (v11-v12)
    k2 = b * v11 * (v22-v12)

    center = p1 + k1 * v1 + k2 * v2

    return center

def Circle_Coordo(coordo: np.ndarray, R: float, n: np.ndarray) -> np.ndarray:
    """Return center from coordinates a radius and and a vector normal to the circle.\n
    return center
    """

    R = np.abs(R)

    coordo = np.reshape(coordo, (-1, 3))

    assert coordo.shape[0] >= 2, 'must give at least 2 points'
    
    n = Point._getCoord(n)

    p0 = np.mean(coordo, 0)
    x0, y0, z0 = coordo[0]        

    def eval(v):
        x,y,z = v
        f = np.linalg.norm(np.linalg.norm(coordo-v, axis=1) - R**2)
        return f

    # point must belong to the plane
    eqPlane = lambda v: v @ n
    cons = ({'type': 'eq', 'fun': eqPlane})
    res = minimize(eval, p0, constraints=cons, tol=1e-12)

    assert res.success, 'the center has not been found'
    center: np.ndarray = res.x

    return center

def Points_IntersectCircles(circle1: Circle, circle2: Circle) -> np.ndarray:
    """Calculates the coordinates at the intersection of the two circles (i,3). This only works if they're on the same plane.

    Parameters
    ----------
    circle1 : Circle
        circle 1
    circle2 : Circle
        circle 2
    """

    r1 = circle1.diam/2
    r2 = circle2.diam/2

    p1 = circle1.center.coordo
    p2 = circle2.center.coordo

    d = np.linalg.norm(p2 - p1)

    if d > r1 + r2:
        print("The circles are separated")
        return None
    elif d < np.abs(r1 - r2):
        print("The circles are concentric")
        return None
    elif d == 0 and r1 == r2:
        print("The circles are the same")
        return None
    
    a = (r1**2  - r2**2 + d**2)/(2*d)
    h = np.sqrt(r1**2 - a**2)

    p3 = p1 + a*(p2-p1)/d

    if d == r1 + r2:
        return p3.reshape(1, 3)
    else:

        i = normalize_vect(p2-p1)
        k = np.array([0,0,1])
        j = np.cross(k, i)

        mat = np.array([i,j,k]).T

        coord = np.zeros((2, 3))
        coord[0,:] = p3 + mat @ np.array([0,-h,0]) 
        coord[1,:] = p3 + mat @ np.array([0,+h,0])
        return coord