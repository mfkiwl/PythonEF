"""Interface module with gmsh (https://gmsh.info/).
This module lets you manipulate Geom objects to create meshes."""

from typing import cast
import gmsh
import sys
import os
import numpy as np
import matplotlib

import Folder
from Geom import *
from GroupElem import GroupElem, ElemType, MatrixType, GroupElem_Factory
from Mesh import Mesh
from TicTac import Tic
import Display as Display
from Materials import _Beam_Model
from Simulations import _Simu

class Interface_Gmsh:

    def __init__(self, openGmsh=False, gmshVerbosity=False, verbosity=False):
        """Building an interface that can interact with gmsh.

        Parameters
        ----------
        openGmsh : bool, optional
            display mesh built in gmsh, by default False
        gmshVerbosity : bool, optional
            gmsh can write to terminal, by default False
        verbosity : bool, optional
            interfaceGmsh class can write construction summary to terminal, by default False
        """
    
        self.__openGmsh = openGmsh
        """gmsh can display the mesh"""
        self.__gmshVerbosity = gmshVerbosity
        """gmsh can write to the console"""
        self.__verbosity = verbosity
        """the interface can write to the console"""

        self._init_gmsh()

        if verbosity:
            Display.Section("Init interface GMSH")

    def __CheckType(self, dim: int, elemType: str):
        """Check that the element type is usable."""
        if dim == 1:
            assert elemType in ElemType.get_1D(), f"Must be in {ElemType.get_1D()}"
        if dim == 2:
            assert elemType in ElemType.get_2D(), f"Must be in {ElemType.get_2D()}"
        elif dim == 3:
            assert elemType in ElemType.get_3D(), f"Must be in {ElemType.get_3D()}"
    
    def _init_gmsh(self, factory: str= 'occ'):
        """Initialize gmsh."""        
        if not gmsh.isInitialized():
            gmsh.initialize()
        if self.__gmshVerbosity == False:
            gmsh.option.setNumber('General.Verbosity', 0)
        gmsh.model.add("model")
        if factory == 'occ':
            self.factory = gmsh.model.occ
        elif factory == 'geo':
            self.factory = gmsh.model.geo
        else:
            raise Exception("Unknow factory")
        return self.factory
        
    def _Loop_From_Geom(self, geom: Union[Circle, Domain, PointsList, Contour]) -> tuple[int, list[int], list[int]]:
        """Creation of a loop based on the geometric object.\n
        return loop, lines, points"""        

        if isinstance(geom, Circle):
            loop, lines, points = self._Loop_From_Circle(geom)[:3]
        elif isinstance(geom, Domain):
            loop, lines, points = self._Loop_From_Domain(geom)[:3]
        elif isinstance(geom, PointsList):
            contour = geom.Get_Contour()            
            loop, lines, points = self._Loop_From_Contour(contour)[:3]
        elif isinstance(geom, Contour):
            loop, lines, points = self._Loop_From_Contour(geom)[:3]
        else:
            raise Exception("Must be a circle, a domain, a list of points or a contour.")
        
        return loop, lines, points
    
    def _Loop_From_Contour(self, contour: Contour) -> tuple[int, list[int], list[int], list[int], list[int]]:
        """Create a loop associated with a list of 1D objects (Line, CircleArc, PointsList).\n
        return loop, lines, points, openLines, openPoints
        """

        factory = self.factory

        points: list[int] = []
        lines: list[int] = []

        nGeom = len(contour.geoms)

        openPoints = []
        openLines = []

        for i, geom in enumerate(contour.geoms):

            assert isinstance(geom, (Line, CircleArc, PointsList)), "Must be a Line, CircleArc or PointsList"

            if i == 0:
                p1 = factory.addPoint(*geom.pt1.coordo, geom.meshSize)
                if geom.pt1.isOpen: openPoints.append(p1)
                p2 = factory.addPoint(*geom.pt2.coordo, geom.meshSize)
                if geom.pt2.isOpen: openPoints.append(p2)
                points.extend([p1,p2])
            elif i > 0 and i+1 < nGeom:
                p1 = p2
                p2 = factory.addPoint(*geom.pt2.coordo, geom.meshSize)
                if geom.pt2.isOpen: openPoints.append(p2)
                points.append(p2)
            else:
                p1 = p2
                p2 = firstPoint

            if isinstance(geom, Line):

                line = factory.addLine(p1, p2)

                if geom.isOpen:
                    openLines.append(line)

                lines.append(line)

            elif isinstance(geom, CircleArc):                

                pC =  factory.addPoint(*geom.center.coordo, geom.meshSize)
                p3 = factory.addPoint(*geom.pt3.coordo)

                if np.abs(geom.angle) > np.pi:
                    line1 = factory.addCircleArc(p1, pC, p3)
                    line2 = factory.addCircleArc(p3, pC, p2)
                    lines.extend([line1, line2])
                    if geom.isOpen:
                        openLines.extend([line1, line2])
                else:                    
                    if factory == gmsh.model.occ:                        
                        line = factory.addCircleArc(p1, p3, p2, center=False)
                    else:
                        n = geom.n
                        line = factory.addCircleArc(p1, pC, p2, nx=n[0], ny=n[1], nz=n[2])
                    lines.append(line)
                    if geom.isOpen:
                        openLines.append(line)
                
                factory.remove([(0,pC)])
                factory.remove([(0,p3)])

            elif isinstance(geom, PointsList):
                
                # get points to construct the spline
                splinePoints = [factory.addPoint(*p.coordo, geom.meshSize) for p in geom.points[1:-1]]                
                splinePoints.insert(0,p1)
                splinePoints.append(p2)

                line = factory.addSpline(splinePoints)
                lines.append(line)
                if geom.isOpen:
                    openLines.append(line)

                factory.remove([(0,p) for p in splinePoints[1:-1]])

            if i == 0:
                firstPoint = p1

        loop = factory.addCurveLoop(lines)

        self.factory.synchronize()

        return loop, lines, points, openLines, openPoints

    def _Loop_From_Circle(self, circle: Circle) -> tuple[int, list[int], list[int]]:
        """Creation of a loop associated with a circle.\n
        return loop, lines, points
        """

        factory = self.factory

        center = circle.center
        rayon = circle.diam/2

        # Circle points                
        p0 = factory.addPoint(*center.coordo, circle.meshSize) # center
        p1 = factory.addPoint(*circle.pt1.coordo, circle.meshSize)
        p2 = factory.addPoint(*circle.pt2.coordo, circle.meshSize)
        p3 = factory.addPoint(*circle.pt3.coordo, circle.meshSize)
        p4 = factory.addPoint(*circle.pt4.coordo, circle.meshSize)
        points = [p1, p2, p3, p4]

        # Circle arcs
        l1 = factory.addCircleArc(p1, p0, p2)
        l2 = factory.addCircleArc(p2, p0, p3)
        l3 = factory.addCircleArc(p3, p0, p4)
        l4 = factory.addCircleArc(p4, p0, p1)
        lines = [l1, l2, l3, l4]

        # Here we remove the point from the center of the circle
        # VERY IMPORTANT otherwise the point remains at the center of the circle.
        # We don't want any points not attached to the mesh
        factory.remove([(0,p0)], False)
        
        loop = factory.addCurveLoop([l1,l2,l3,l4])

        return loop, lines, points

    def _Loop_From_Domain(self, domain: Domain) -> int:
        """Create a loop associated with a domain.\n
        return loop, lines, points, openPoints
        """
        pt1 = domain.pt1
        pt2 = domain.pt2
        mS = domain.meshSize

        factory = self.factory

        p1 = factory.addPoint(pt1.x, pt1.y, pt1.z, mS)
        p2 = factory.addPoint(pt2.x, pt1.y, pt1.z, mS)
        p3 = factory.addPoint(pt2.x, pt2.y, pt1.z, mS)
        p4 = factory.addPoint(pt1.x, pt2.y, pt1.z, mS)
        points = [p1,p2,p3,p4]

        l1 = factory.addLine(p1, p2)
        l2 = factory.addLine(p2, p3)
        l3 = factory.addLine(p3, p4)
        l4 = factory.addLine(p4, p1)
        lines = [l1,l2,l3,l4]

        loop = factory.addCurveLoop(lines)
        
        return loop, lines, points

    def _Surface_From_Loops(self, loops: list[int]) -> tuple[int, int]:
        """Create a surface associated with a loop (must be a plane surface).\n
        return surface
        """
        # must form a plane surface
        surface = self.factory.addPlaneSurface(loops)
        return surface
    
    def _Surfaces(self, contour: Geom, inclusions: list[Geom]=[],
                  elemType=ElemType.TRI3, isOrganised=False) -> tuple[list[int],list[int],list[int]]:
        """Create surfaces. Must be plane surfaces otherwse use 'factory.addSurfaceFilling' \n
        return surfaces, lines, points

        Parameters
        ----------
        contour : Geom
            the object that creates the surface area
        inclusions : list[Geom]
            objects that create hollow or filled surfaces in the first surface.\n
            CAUTION : all inclusions must be contained within the contour and do not cross
        elemType : ElemType, optional
            element type used, by default TRI3
        isOrganised : bool, optional
            mesh is organized, by default False
        """

        factory = self.factory

        # Create contour surface
        loopContour, lines, points = self._Loop_From_Geom(contour)

        # Creation of all loops associated with objects within the domain
        hollowLoops, filledLoops = self.__Get_hollow_And_filled_Loops(inclusions)
        
        loops = [loopContour] # domain surface
        loops.extend(hollowLoops) # Hollow contours are added
        loops.extend(filledLoops) # Filled contours are added

        surfaces = [self._Surface_From_Loops(loops)] # first filled surface

        # For each filled object, it is necessary to create a surface
        [surfaces.append(factory.addPlaneSurface([loop])) for loop in filledLoops]

        self._OrganiseSurfaces(surfaces, elemType, isOrganised)

        return surfaces, lines, points
    
    def _OrganiseSurfaces(self, surfaces: list[int], elemType: ElemType,
                           isOrganised=False, numElems:list[int]=[]) -> None:

        self.factory.synchronize()

        setRecombine = elemType in [ElemType.QUAD4, ElemType.QUAD8,
                                    ElemType.HEXA8, ElemType.HEXA20]
        
        for surf in surfaces:

            lines = gmsh.model.getBoundary([(2, surf)])
            if len(lines) == len(numElems):
                [gmsh.model.mesh.setTransfiniteCurve(l[1], int(n+1))
                    for l, n in zip(lines, numElems)]

            if isOrganised:
                if len(lines) == 4:
                    # only works if the surface is formed by 4 lines
                    gmsh.model.mesh.setTransfiniteSurface(surf)

            if setRecombine:
                # https://onelab.info/pipermail/gmsh/2010/005359.html
                gmsh.model.mesh.setRecombine(2, surf)
    
    def _Spline_From_Points(self, pointsList: PointsList) -> tuple[int, list[int]]:

        meshSize = pointsList.meshSize
        gmshPoints = [self.factory.addPoint(*p.coordo, meshSize) for p in pointsList.points]        
        
        spline = self.factory.addSpline(gmshPoints)
        # remove all points except the first and the last points
        self.factory.remove([(0,p) for p in gmshPoints[1:-1]])

        points = [gmshPoints[0], gmshPoints[-1]]

        return spline, points
    
    __dict_name_dim = {
        0 : "P",
        1 : "L",
        2 : "S",
        3 : "V"
    }

    def _Set_PhysicalGroups(self, setPoints=True, setLines=True, setSurfaces=True, setVolumes=True) -> None:
        """Create physical groups based on model entities."""
        self.factory.synchronize()        
        entities = np.array(gmsh.model.getEntities())

        if entities.size == 0: return
        
        listDim = []
        if setPoints: listDim.append(0)            
        if setLines: listDim.append(1)            
        if setSurfaces: listDim.append(2)            
        if setVolumes: listDim.append(3)

        def _addPhysicalGroup(dim: int, tag: int, t:int) -> None:
            name = f"{self.__dict_name_dim[dim]}{t}"
            gmsh.model.addPhysicalGroup(dim, [tag], name=name)

        for dim in listDim:
            idx = entities[:,0]==dim
            tags = entities[idx, 1]
            [_addPhysicalGroup(dim, tag, t) for t, tag in enumerate(tags)]

    def _Extrude(self, surfaces: list[int], extrude=[0,0,1], elemType=ElemType.TETRA4, layers:list[int]=[]) -> list[tuple]:
        """Function that extrudes multiple surfaces

        Parameters
        ----------
        surfaces : list[int]
            list of surfaces
        extrude : list, optional
            extrusion directions and values, by default [0,0,1]
        elemType : ElemType, optional
            element type used, by default "HEXA8"        
        layers: list[int], optional
            layers in extrusion, by default []
        """
        
        factory = self.factory

        extruEntities = []

        if "TETRA" in elemType:
            recombine = False
        else:
            recombine = True
            if len(layers) == 0:
                layers = [1]

        entites = [(2, surf) for surf in surfaces]
        extru = factory.extrude(entites, *extrude, recombine=recombine, numElements=layers)
        extruEntities.extend(extru)

        return extruEntities
    
    def _Revolve(self, surfaces: list[int], axis: Line, angle: float= np.pi*2, elemType: ElemType=ElemType.TETRA4, layers:list[int]=[30]) -> list[tuple]:
        """Function that revolves multiple surfaces.

        Parameters
        ----------
        surfaces : list[int]
            list of surfaces
        axis : Line
            revolution axis
        angle: float, optional
            revolution angle, by default 2*pi
        elemType : ElemType, optional
            element type used
        layers: list[int], optional
            layers in extrusion, by default [30]
        """
        
        factory = self.factory

        angleIs2PI = np.abs(angle) == 2 * np.pi

        if angleIs2PI:
            angle = angle / 2
            layers = [l//2 for l in layers]

        revolEntities = []

        if "TETRA" in elemType:
            recombine = False
        else:
            recombine = True
            if len(layers) == 0:
                layers = [3]

        entities = [(2,s) for s in surfaces]

        p0 = axis.pt1.coordo
        a0 = normalize_vect(axis.pt2.coordo - p0)

        # Create new entites for revolution
        revol = factory.revolve(entities, *p0, *a0, angle, layers, recombine=recombine)
        revolEntities.extend(revol)

        if angleIs2PI:
            revol = factory.revolve(entities, *p0, *a0, -angle, layers, recombine=recombine)
            revolEntities.extend(revol)

        return revolEntities
    
    def _Link_Contours(self, contour1: Contour, contour2: Contour, elemType: ElemType,
                      nLayers:int=0, numElems:list[int]=[]) -> list[tuple]:
        """Link 2 contours and create a volume. Contours must be connectable, i.e. they must have the same number of points and lines.

        Parameters
        ----------
        contour1 : Contour
            the first contour
        contour2 : Contour
            the second contour
        elemType : ElemType
            element type used to mesh
        nLayers : int, optional
            number of layers joining the contours, by default 0
        numElems : list[int], optional
            number of elements for each lines in contour, by default []

        Returns
        -------
        list[tuple]
            created entities
        """

        tic = Tic()

        factory = self.factory

        
        # specifies whether contour surfaces can be organized
        canBeOrganised = len(contour1.geoms) == 4
        # specifies if it is necessary to recombine bonding surfaces
        recombineLinkingSurf = 'HEXA' in elemType or 'PRISM' in elemType
        useTransfinite = canBeOrganised and recombineLinkingSurf
        
        loop1, lines1, points1 = self._Loop_From_Geom(contour1)
        loop2, lines2, points2 = self._Loop_From_Geom(contour2)

        surf1 = factory.addSurfaceFilling(loop1) # here we dont use self._Surfaces()
        surf2 = factory.addSurfaceFilling(loop2)

        # append entities together
        points = points1.copy(); points.extend(points2)
        lines = lines1.copy(); lines.extend(lines2)
        surfaces = [surf1, surf2]

        if useTransfinite:
            if len(numElems) == 0:                
                numElems = [int(geom.length / geom.meshSize) for geom in contour1.geoms]            
                assert len(numElems) == len(lines1)
        self._OrganiseSurfaces(surfaces, elemType, canBeOrganised, numElems)

        # check that the given entities are linkable
        assert len(lines1) == len(lines2), "Must provide same number of lines."
        nP, nL = len(points1), len(lines1)
        assert nP == nL, "Must provide the same number of points as lines."

        nLayers = int(nLayers)

        # create linking between every points belonging to points1 and points2
        linkingLines = [factory.addLine(pi,pj) for pi, pj in zip(points1, points2)]

        lines.extend(linkingLines)

        if nLayers > 0:
            # specifies the number of elements in the lines
            factory.synchronize()
            [gmsh.model.mesh.setTransfiniteCurve(l, nLayers+1) for l in linkingLines]

        # def CreateLinkingSurface(i: int):
        for i in range(nP):
            j = i+1 if i+1 < nP else 0
            
            # get the lines to construct the surfaces
            l1 = lines1[i]
            l2 = linkingLines[j]
            l3 = lines2[i]
            l4 = linkingLines[i]
            # get the points of the surface
            p1, p2 = points1[i], points1[j]
            p3, p4 = points2[i], points2[j]
            # loop to create the surface (- are optionnal)
            loop = factory.addCurveLoop([l1,l2,-l3,-l4])
            # create the surface and add it to linking surfaces
            surf = factory.addSurfaceFilling(loop)
            surfaces.append(surf)
            
            if nLayers > 0:
                factory.synchronize()
                # surf must be transfinite to have a strucutred surfaces during the extrusion
                gmsh.model.mesh.setTransfiniteSurface(surf, cornerTags=[p1,p2,p3,p4])

            if recombineLinkingSurf:
                if nLayers == 0: factory.synchronize()
                # must recombine the surface in case we use PRISM or HEXA elements
                gmsh.model.mesh.setRecombine(2, surf)
        
        vol = factory.addSurfaceLoop(surfaces)
        factory.addVolume([vol])

        if useTransfinite:
            factory.synchronize()
            gmsh.model.mesh.setTransfiniteVolume(vol, points)

        tic.Tac("Mesh","Link contours", self.__verbosity)

        # return entities
        entities = self.Get_Entities(points, lines, surfaces, [vol])

        return entities
    
    @staticmethod
    def Get_Entities(points=[], lines=[], surfaces=[], volumes=[]) -> list[tuple]:
        entities = []
        entities.extend([(0,p) for p in points])
        entities.extend([(1,l) for l in lines])
        entities.extend([(2,s) for s in surfaces])
        entities.extend([(3,v) for v in volumes])
        return entities

    def Mesh_Import_mesh(self, mesh: str, setPhysicalGroups=False, coef=1.0):
        """Importing an .msh file. Must be an gmsh file.

        Parameters
        ----------
        mesh : str
            file (.msh) that gmsh will load to create the mesh        
        setPhysicalGroups : bool, optional
            retrieve entities to create physical groups of elements, by default False
        coef : float, optional
            coef applied to node coordinates, by default 1.0

        Returns
        -------
        Mesh
            Built mesh
        """

        self._init_gmsh()

        tic = Tic()

        gmsh.open(mesh)
        
        tic.Tac("Mesh","Mesh import", self.__verbosity)

        if setPhysicalGroups:
            self._Set_PhysicalGroups()

        return self._Construct_Mesh(coef)

    def Mesh_Import_part(self, file: str, dim: int, meshSize=0.0, elemType: ElemType=None, refineGeoms=[None], folder=""):
        """Build mesh from imported file (.stp or .igs).\n
        You can only use triangles or tetrahedrons.

        Parameters
        ----------
        file : str
            file (.stp, .igs) that gmsh will load to create the mesh.\n
            Note that for igs files, entities cannot be recovered.
        meshSize : float, optional
            mesh size, by default 0.0
        elemType : ElemType, optional
            element type, by default "TRI3" or "TETRA4" depending on dim.
        refineGeoms : list[Domain|Circle|str]
            Geometric objects to refine de background mesh
        folder : str, optional
            mesh save folder mesh.msh, by default ""

        Returns
        -------
        Mesh
            Built mesh
        """
        
        # Allow other meshes -> this seems impossible - you have to create the mesh using gmsh to control the type of element.

        if elemType is None:
            elemType = ElemType.TRI3 if dim == 2 else ElemType.TETRA4

        self._init_gmsh('occ') # Only work with occ !! Do not change

        assert meshSize >= 0.0, "Must be greater than or equal to 0."
        self.__CheckType(dim, elemType)
        
        tic = Tic()

        factory = self.factory

        if '.stp' in file or '.igs' in file:
            factory.importShapes(file)
        else:
            print("Must be a .stp or .igs file")

        if meshSize > 0:
            self.Set_meshSize(meshSize)

        self._RefineMesh(refineGeoms, meshSize)

        self._Set_PhysicalGroups(setPoints=False, setLines=True, setSurfaces=True, setVolumes=False)

        gmsh.option.setNumber("Mesh.MeshSizeMin", meshSize)
        gmsh.option.setNumber("Mesh.MeshSizeMax", meshSize)

        tic.Tac("Mesh","File import", self.__verbosity)

        self._Meshing(dim, elemType, folder=folder)

        return self._Construct_Mesh()

    def _Cracks_SetPhysicalGroups(self, cracks: list, entities: list[tuple]) -> tuple[int, int, int, int]:
        """Creation of physical groups associated with cracks embeded in entities.\n
        return crackLines, crackSurfaces, openPoints, openLines
        """

        factory = self.factory
        factory.synchronize()

        if len(cracks) == 0:
            return None, None, None, None
        
        # lists containing open entities
        crack1D = []; openPoints = []
        crack2D = []; openLines = []

        entities0D = []
        entities1D = []
        entities2D = []

        for crack in cracks:
            if isinstance(crack, Line): # 1D CRACK
                # Creating points
                pt1 = crack.pt1
                p1 = factory.addPoint(pt1.x, pt1.y, pt1.z, crack.meshSize)
                pt2 = crack.pt2
                p2 = factory.addPoint(pt2.x, pt2.y, pt2.z, crack.meshSize)
                entities0D.extend([p1,p2])

                # Line creation
                line = factory.addLine(p1, p2)
                entities1D.append(line)

                if crack.isOpen:
                    crack1D.append(line)                
                    if pt1.isOpen: openPoints.append(p1)                        
                    if pt2.isOpen: openPoints.append(p2)

            elif isinstance(crack, PointsList):  # 1D CRACK

                line, points = self._Spline_From_Points(crack)
                
                entities0D.extend(points)
                entities1D.append(line)
                
                if crack.isOpen:
                    crack1D.append(line)                    
                    if crack.pt1.isOpen: openPoints.append(points[0])
                    if crack.pt2.isOpen: openPoints.append(points[1])

            elif isinstance(crack, Contour):  # 2D CRACK

                loop, lines, points, openLns, openPts = self._Loop_From_Contour(crack)
                surf = self._Surface_From_Loops([loop])
                
                entities0D.extend(points)
                entities1D.extend(lines)
                entities2D.append(surf)

                if crack.isOpen:
                    crack2D.append(surf)
                    openLines.extend(openLns)                    
                    openPoints.extend(openPts)

            elif isinstance(crack, CircleArc): # 1D CRACK
                
                # add points
                pC =  factory.addPoint(*crack.center.coordo, crack.meshSize)
                p1 = factory.addPoint(*crack.pt1.coordo, crack.meshSize)
                p2 = factory.addPoint(*crack.pt2.coordo, crack.meshSize)
                p3 = factory.addPoint(*crack.pt3.coordo, crack.meshSize)
                entities0D.extend([p1,p2,p3])

                # add lines
                line1 = factory.addCircleArc(p1, pC, p3)
                line2 = factory.addCircleArc(p3, pC, p2)
                lines = [line1, line2]
                entities1D.extend(lines)

                if crack.isOpen:
                    crack1D.extend(lines)
                    if crack.pt1.isOpen: openPoints.append(p1)
                    if crack.pt2.isOpen: openPoints.append(p2)
                    if crack.pt3.isOpen: openPoints.append(p3)
                
                factory.remove([(0,pC)], False)                

            else:

                raise Exception("crack must be a Line, PointsList, Contour or CircleArc")            

        newEntities = [(0, point) for point in entities0D]
        newEntities.extend([(1, line) for line in entities1D])
        newEntities.extend([(2, surf) for surf in entities2D])

        if factory == gmsh.model.occ:
            o, m = gmsh.model.occ.fragment(entities, newEntities)

        factory.synchronize()

        crackLines = gmsh.model.addPhysicalGroup(1, crack1D) if len(crack1D) > 0 else None
        crackSurfaces = gmsh.model.addPhysicalGroup(2, crack2D) if len(crack2D) > 0 else None

        openPoints = gmsh.model.addPhysicalGroup(0, openPoints) if len(openPoints) > 0 else None
        openLines = gmsh.model.addPhysicalGroup(1, openLines) if len(openLines) > 0 else None

        return crackLines, crackSurfaces, openPoints, openLines

    def Mesh_Beams(self, beams: list[_Beam_Model], elemType=ElemType.SEG2, folder=""):
        """Construction of a segment mesh

        Parameters
        beams
        listBeam : list[_Beam_Model]
            list of Beams
        elemType : str, optional
            element type, by default "SEG2" ["SEG2", "SEG3", "SEG4"]
        folder : str, optional
            mesh save folder mesh.msh, by default ""

        Returns
        -------
        Mesh
            construct mesh
        """

        self._init_gmsh()
        self.__CheckType(1, elemType)

        tic = Tic()
        
        factory = self.factory

        points = [] 
        lines = []

        for beam in beams:
            line = beam.line
            
            pt1 = line.pt1; x1 = pt1.x; y1 = pt1.y; z1 = pt1.z
            pt2 = line.pt2; x2 = pt2.x; y2 = pt2.y; z2 = pt2.z

            p1 = factory.addPoint(x1, y1, z1, line.meshSize)
            p2 = factory.addPoint(x2, y2, z2, line.meshSize)
            points.append(p1)
            points.append(p2)

            line = factory.addLine(p1, p2)
            lines.append(line)
        
        factory.synchronize()
        self._Set_PhysicalGroups(setLines=False)

        tic.Tac("Mesh","Beam mesh construction", self.__verbosity)

        self._Meshing(1, elemType, folder=folder)

        mesh = self._Construct_Mesh()

        def FuncAddTags(beam: _Beam_Model):
            nodes = mesh.Nodes_Line(beam.line)
            for grp in mesh.Get_list_groupElem():
                grp.Set_Nodes_Tag(nodes, beam.name)
                grp.Set_Elements_Tag(nodes, beam.name)

        [FuncAddTags(beam) for beam in beams]

        return mesh

    def __Get_hollow_And_filled_Loops(self, inclusions: list[Geom]) -> tuple[list, list]:
        """Creation of hollow and filled loops

        Parameters
        ----------
        inclusions : Circle | Domain | PointsList | Contour
            List of geometric objects contained in the domain

        Returns
        -------
        tuple[list, list]
            all loops created, followed by full (non-hollow) loops
        """
        hollowLoops = []
        filledLoops = []
        for objetGeom in inclusions:
            
            loop = self._Loop_From_Geom(objetGeom)[0]

            if objetGeom.isHollow:
                hollowLoops.append(loop)
            else:                
                filledLoops.append(loop)

        return hollowLoops, filledLoops    

    def Mesh_2D(self, contour: Geom, inclusions: list[Geom]=[], elemType=ElemType.TRI3,
                cracks:list[Geom]=[], refineGeoms: list[Union[Geom,str]]=[],
                isOrganised=False, surfaces:list[tuple[Geom, list[Geom]]]=[], folder=""):
        """Build the 2D mesh by creating a surface from a contour and inclusions

        Parameters
        ----------
        contour : Geom
            geometry that builds the contour
        inclusions : list[Domain, Circle, PointsList, Contour], optional
            list of hollow and non-hollow objects inside the domain 
        elemType : str, optional
            element type, by default "TRI3" ["TRI3", "TRI6", "TRI10", "QUAD4", "QUAD8"]
        cracks : list[Line | PointsList | Countour]
            list of object used to create cracks        
        refineGeoms : list[Domain|Circle|str], optional
            geometric objects for mesh refinement, by default []
        isOrganised : bool, optional
            mesh is organized, by default False
        surfaces : list[tuple[Geom, list[Geom]]]
            additional surfaces. Ex = [(Domain, [Circle, Contour, PointsList])]
        folder : str, optional
            mesh save folder mesh.msh, by default ""

        Returns
        -------
        Mesh
            2D mesh
        """

        self._init_gmsh('occ')
        self.__CheckType(2, elemType)

        tic = Tic()

        factory = self.factory

        self._Surfaces(contour, inclusions, elemType, isOrganised)

        for surface in surfaces:
            factory.synchronize()
            ents = factory.getEntities(2)
            newSurfaces = self._Surfaces(surface[0], surface[1], elemType, isOrganised)[0]
            factory.fragment(ents, [(2, surf) for surf in newSurfaces])        

        # Recovers 2D entities
        factory.synchronize()
        entities2D = gmsh.model.getEntities(2)

        # Crack creation
        crackLines, crackSurfaces, openPoints, openLines = self._Cracks_SetPhysicalGroups(cracks, entities2D)

        if (len(cracks) > 0 and 'QUAD' in elemType) or len(surfaces) > 0:
            # dont delete
            surfaceTags = [s[1] for s in gmsh.model.getEntities(2)]
            self._OrganiseSurfaces(surfaceTags, elemType, isOrganised)

        self._RefineMesh(refineGeoms, contour.meshSize)

        self._Set_PhysicalGroups()

        tic.Tac("Mesh","Geometry", self.__verbosity)

        self._Meshing(2, elemType, crackLines=crackLines, openPoints=openPoints, folder=folder)

        return self._Construct_Mesh()

    def Mesh_3D(self, contour: Geom, inclusions: list[Geom]=[],
                extrude=[0,0,1], layers:list[int]=[], elemType=ElemType.TETRA4,
                cracks: list[Geom]=[], refineGeoms: list[Union[Geom,str]]=[],
                isOrganised=False, surfaces:list[tuple[Geom, list[Geom]]]=[], folder="") -> Mesh:
        """Build the 3D mesh by creating a surface from a Geom object

        Parameters
        ----------
        contour : Geom
            geometry that builds the contour
        inclusions : list[Domain, Circle, PointsList, Contour], optional
            list of hollow and non-hollow objects inside the domain
        extrude : list, optional
            extrusion, by default [0,0,1]
        layers: list[int], optional
            layers in extrusion, by default []
        elemType : str, optional
            element type, by default "TETRA4" ["TETRA4", "TETRA10", "HEXA8", "HEXA20", "PRISM6", "PRISM15"]
        cracks : list[Line | PointsList | Countour]
            list of object used to create cracks
        refineGeoms : list[Domain|Circle|str], optional
            geometric objects for mesh refinement, by default []
        isOrganised : bool, optional
            mesh is organized, by default False
        surfaces : list[tuple[Geom, list[Geom]]]
            additional surfaces. Ex = [(Domain, [Circle, Contour, PointsList])]
        folder : str, optional
            mesh.msh backup folder, by default ""

        Returns
        -------
        Mesh
            3D mesh
        """
        
        self._init_gmsh()
        self.__CheckType(3, elemType)
        
        tic = Tic()

        factory = self.factory

        self._Surfaces(contour, inclusions)
        for surface in surfaces:
            factory.synchronize()
            ents = factory.getEntities(2)
            newSurfaces = self._Surfaces(surface[0], surface[1])[0]
            factory.fragment(ents, [(2, surf) for surf in newSurfaces])

        # get created surfaces
        factory.synchronize()
        surfaces = [entity[1] for entity in factory.getEntities(2)]
        self._OrganiseSurfaces(surfaces, elemType, isOrganised)

        self._Extrude(surfaces=surfaces, extrude=extrude, elemType=elemType, layers=layers)

        # Recovers 3D entities
        factory.synchronize()
        entities3D = gmsh.model.getEntities(3)

        # Crack creation
        crackLines, crackSurfaces, openPoints, openLines = self._Cracks_SetPhysicalGroups(cracks, entities3D)

        self._RefineMesh(refineGeoms, contour.meshSize)

        self._Set_PhysicalGroups()

        tic.Tac("Mesh","Geometry", self.__verbosity)

        self._Meshing(3, elemType, folder=folder, crackLines=crackLines, crackSurfaces=crackSurfaces, openPoints=openPoints, openLines=openLines)
        
        return self._Construct_Mesh()
    
    def Mesh_Revolve(self, contour: Geom, inclusions: list[Geom]=[],
                     axis: Line=Line(Point(), Point(0,1)), angle=2*np.pi, layers:list[int]=[30], elemType=ElemType.TETRA4,
                     cracks: list[Geom]=[], refineGeoms: list[Union[Geom,str]]=[],
                     isOrganised=False, surfaces:list[tuple[Geom, list[Geom]]]=[],  folder="") -> Mesh:
        """Builds a 3D mesh by rotating a surface along an axis.

        Parameters
        ----------
        contour : Geom
            geometry that builds the contour
        inclusions : list[Domain, Circle, PointsList, Contour], optional
            list of hollow and non-hollow objects inside the domain
        axis : Line, optional
            revolution axis, by default Line(Point(), Point(0,1))
        angle : _type_, optional
            revolution angle, by default 2*np.pi
        layers: list[int], optional
            layers in extrusion, by default [30]
        elemType : ElemType, optional
            element type, by default "TETRA4" ["TETRA4", "TETRA10", "HEXA8", "HEXA20", "PRISM6", "PRISM15"]
        cracks : list[Line | PointsList | Countour]
            list of object used to create cracks
        refineGeoms : list[Domain|Circle|str], optional
            geometric objects for mesh refinement, by default []
        isOrganised : bool, optional
            mesh is organized, by default False
        surfaces : list[tuple[Geom, list[Geom]]]
            additional surfaces. Ex = [(Domain, [Circle, Contour, PointsList])]
        folder : str, optional
            mesh.msh backup folder, by default ""

        Returns
        -------
        Mesh
            3D mesh
        """

        self._init_gmsh()
        self.__CheckType(3, elemType)
        
        tic = Tic()
        
        factory = self.factory

        self._Surfaces(contour, inclusions)
        for surface in surfaces:
            factory.synchronize()
            ents = factory.getEntities(2)
            newSurfaces = self._Surfaces(surface[0], surface[1])[0]
            factory.fragment(ents, [(2, surf) for surf in newSurfaces])

        # get created surfaces
        factory.synchronize()
        surfaces = [entity[1] for entity in factory.getEntities(2)]
        self._OrganiseSurfaces(surfaces, elemType, isOrganised)
        
        self._Revolve(surfaces=surfaces, axis=axis, angle=angle, elemType=elemType, layers=layers)

        # Recovers 3D entities
        self.factory.synchronize()
        entities3D = gmsh.model.getEntities(3)

        # Crack creation
        crackLines, crackSurfaces, openPoints, openLines = self._Cracks_SetPhysicalGroups(cracks, entities3D)

        self._RefineMesh(refineGeoms, contour.meshSize)

        self._Set_PhysicalGroups()

        tic.Tac("Mesh","Geometry", self.__verbosity)

        self._Meshing(3, elemType, folder=folder, crackLines=crackLines, crackSurfaces=crackSurfaces, openPoints=openPoints, openLines=openLines)

        return self._Construct_Mesh()
    
    def Create_posFile(self, coordo: np.ndarray, values: np.ndarray, folder: str, filename="data") -> str:
        """Creation of a .pos file that can be used to refine a mesh in a zone.

        Parameters
        ----------
        coordo : np.ndarray
            coordinates of values
        values : np.ndarray
            values at coordinates
        folder : str
            backup file
        filename : str, optional
            pos file name, by default "data".

        Returns
        -------
        str
            Returns path to .pos file
        """

        assert isinstance(coordo, np.ndarray), "Must be a numpy array"
        assert coordo.shape[1] == 3, "Must be of dimension (n, 3)"

        assert values.shape[0] == coordo.shape[0], "values and coordo are the wrong size"

        data = np.append(coordo, values.reshape(-1, 1), axis=1)

        self._init_gmsh()

        view = gmsh.view.add("scalar points")

        gmsh.view.addListData(view, "SP", coordo.shape[0], data.reshape(-1))

        path = Folder.New_File(f"{filename}.pos", folder)

        gmsh.view.write(view, path)

        return path
    
    def Set_meshSize(self, meshSize:float) -> None:
        """Sets the mesh size"""
        self.factory.synchronize()
        gmsh.model.mesh.setSize(self.factory.getEntities(0), meshSize)
    
    def _RefineMesh(self, refineGeoms: list[Union[Domain,Circle,str]], meshSize: float):
        """Sets a background mesh

        Parameters
        ----------
        refineGeoms : list[Domain|Circle|str]
            Geometric objects to refine de background mesh
        meshSize : float
            size of elements outside the domain
        """

        # See t10.py in the gmsh tutorials
        # https://gitlab.onelab.info/gmsh/gmsh/blob/master/tutorials/python/t10.py

        if refineGeoms is None or len(refineGeoms) == 0: return

        fields = []

        for geom in refineGeoms:

            if isinstance(geom, Domain):

                coordo = np.array([point.coordo  for point in geom.points])

                field = gmsh.model.mesh.field.add("Box")
                gmsh.model.mesh.field.setNumber(field, "VIn", geom.meshSize)
                gmsh.model.mesh.field.setNumber(field, "VOut", meshSize)
                gmsh.model.mesh.field.setNumber(field, "XMin", coordo[:,0].min())
                gmsh.model.mesh.field.setNumber(field, "XMax", coordo[:,0].max())
                gmsh.model.mesh.field.setNumber(field, "YMin", coordo[:,1].min())
                gmsh.model.mesh.field.setNumber(field, "YMax", coordo[:,1].max())
                gmsh.model.mesh.field.setNumber(field, "ZMin", coordo[:,2].min())
                gmsh.model.mesh.field.setNumber(field, "ZMax", coordo[:,2].max())

            elif isinstance(geom, Circle):

                pC = geom.center
                field = gmsh.model.mesh.field.add("Cylinder")
                gmsh.model.mesh.field.setNumber(field, "VIn", geom.meshSize)
                gmsh.model.mesh.field.setNumber(field, "VOut", meshSize)
                gmsh.model.mesh.field.setNumber(field, "Radius", geom.diam/2)
                gmsh.model.mesh.field.setNumber(field, "XCenter", pC.x)
                gmsh.model.mesh.field.setNumber(field, "YCenter", pC.y)
                gmsh.model.mesh.field.setNumber(field, "ZCenter", pC.z)

            elif isinstance(geom, str):

                if not Folder.Exists(geom) :
                    print("The .pos file does not exist.")
                    continue

                if ".pos" not in geom:
                    print("Must provide a .pos file")
                    continue

                gmsh.merge(geom)

                # Add the post-processing view as a new size field:
                field = gmsh.model.mesh.field.add("PostView")
                # gmsh.model.mesh.field.setNumber(field, "ViewIndex", 0)
                # gmsh.model.mesh.field.setNumber(field, "UseClosest", 0)

            elif geom is None:
                continue

            else:
                print("refineGeoms must be of type Domain, Circle, str(.pos file)")
            
            fields.append(field)

        # Let's use the minimum of all the fields as the mesh size field:
        minField = gmsh.model.mesh.field.add("Min")
        gmsh.model.mesh.field.setNumbers(minField, "FieldsList", fields)
        gmsh.model.mesh.field.setAsBackgroundMesh(minField)

        # Finally, while the default "Frontal-Delaunay" 2D meshing algorithm
        # (Mesh.Algorithm = 6) usually leads to the highest quality meshes, the
        # "Delaunay" algorithm (Mesh.Algorithm = 5) will handle complex mesh size fields
        # better - in particular size fields with large element size gradients:
        gmsh.option.setNumber("Mesh.Algorithm", 5)

    @staticmethod
    def _Set_mesh_order(elemType: str):
        """Set mesh order"""
        if elemType in ["TRI3","QUAD4"]:
            gmsh.model.mesh.set_order(1)
        elif elemType in ["SEG3", "TRI6", "QUAD8", "TETRA10", "HEXA20", "PRISM15"]:
            if elemType in ["QUAD8", "HEXA20", "PRISM15"]:
                gmsh.option.setNumber('Mesh.SecondOrderIncomplete', 1)
            gmsh.model.mesh.set_order(2)
        elif elemType in ["SEG4", "TRI10"]:
            gmsh.model.mesh.set_order(3)
        elif elemType in ["SEG5", "TRI15"]:
            gmsh.model.mesh.set_order(4)

    def _Set_algorithm(self, elemType: ElemType) -> None:
        """Set the mesh algorithm.\n
        Mesh.Algorithm
            2D mesh algorithm (1: MeshAdapt, 2: Automatic, 3: Initial mesh only, 5: Delaunay, 6: Frontal-Delaunay, 7: BAMG, 8: Frontal-Delaunay for Quads, 9: Packing of Parallelograms, 11: Quasi-structured Quad)
            Default value: 6

        Mesh.Algorithm3D
            3D mesh algorithm (1: Delaunay, 3: Initial mesh only, 4: Frontal, 7: MMG3D, 9: R-tree, 10: HXT)
            Default value: 1            

        Mesh.RecombinationAlgorithm
            Mesh recombination algorithm (0: simple, 1: blossom, 2: simple full-quad, 3: blossom full-quad)
            Default value: 1        

        Mesh.SubdivisionAlgorithm
            Mesh subdivision algorithm (0: none, 1: all quadrangles, 2: all hexahedra, 3: barycentric)
            Default value: 0
        """

        if elemType in ElemType.get_1D() or elemType in ElemType.get_2D():
            meshAlgorithm = 6 # 6: Frontal-Delaunay
        elif elemType in ElemType.get_3D():
            meshAlgorithm = 1 # 1: Delaunay
        gmsh.option.setNumber("Mesh.Algorithm", meshAlgorithm)

        recombineAlgorithm = 1
        if elemType in [ElemType.QUAD4, ElemType.QUAD8]:
            subdivisionAlgorithm = 1
        else:
            subdivisionAlgorithm = 0        

        gmsh.option.setNumber("Mesh.RecombinationAlgorithm", recombineAlgorithm)
        gmsh.option.setNumber("Mesh.SubdivisionAlgorithm", subdivisionAlgorithm)

    def _Meshing(self, dim: int, elemType: str,
                 crackLines:int=None, crackSurfaces:int=None, openPoints:int=None, openLines:int=None,
                 folder="", filename="mesh"):
        """Construction of gmsh mesh from geometry that has been built or imported.

        Parameters
        ----------
        dim : int
            mesh size
        elemType : str
            element type
        crackLines : int, optional
            physical group for crack lines (associated with openPoints), by default None
        crackSurfaces : int, optional
            physical group for crack surfaces (associated with openLines), by default None
        openPoints: int, optional
            physical group for open points, by default None
        openLines : int, optional
            physical group for open lines, by default None
        folder : str, optional
            mesh save folder mesh.msh, by default ""
        filename : str, optional
            saving file filename.msh, by default mesh
        """
        # TODO make sure that physical groups have been created
        
        self._Set_algorithm(elemType)
        self.factory.synchronize()

        tic = Tic()

        gmsh.model.mesh.generate(dim)
        
        # set mest order
        Interface_Gmsh._Set_mesh_order(elemType)

        if dim > 1:
            # remove all duplicated nodes and elements
            gmsh.model.mesh.removeDuplicateNodes()
            gmsh.model.mesh.removeDuplicateElements()

        # PLUGIN CRACK
        if crackSurfaces != None or crackLines != None:

            if crackLines != None: # 1D CRACKS
                gmsh.plugin.setNumber("Crack", "Dimension", 1)
                gmsh.plugin.setNumber("Crack", "PhysicalGroup", crackLines)
                if openPoints != None:
                    gmsh.plugin.setNumber("Crack", "OpenBoundaryPhysicalGroup", openPoints)
                gmsh.plugin.run("Crack") # DONT DELETE must be called for lines and surfaces
            
            if crackSurfaces != None: # 2D CRACKS                
                gmsh.plugin.setNumber("Crack", "Dimension", 2)
                gmsh.plugin.setNumber("Crack", "PhysicalGroup", crackSurfaces)
                if openLines != None:
                    gmsh.plugin.setNumber("Crack", "OpenBoundaryPhysicalGroup", openLines)
                gmsh.plugin.run("Crack")
        
        # Open gmsh interface if necessary
        if '-nopopup' not in sys.argv and self.__openGmsh:
            gmsh.fltk.run()
        
        tic.Tac("Mesh","Meshing with gmsh", self.__verbosity)

        if folder != "":
            # gmsh.write(Dossier.Join([folder, "model.geo"])) # It doesn't seem to work, but that's okay
            self.factory.synchronize()

            if not os.path.exists(folder):
                os.makedirs(folder)
            msh = Folder.Join(folder, f"{filename}.msh")
            gmsh.write(msh)
            tic.Tac("Mesh","Saving .msh", self.__verbosity)

    def _Construct_Mesh(self, coef=1) -> Mesh:
        """Recovering the built mesh"""

        # Old method was boggling
        # The bugs have been fixed because I didn't properly organize the nodes when I created them
        # https://gitlab.onelab.info/gmsh/gmsh/-/issues/1926
        
        tic = Tic()

        dict_groupElem = {}
        meshDim = gmsh.model.getDimension()
        elementTypes = gmsh.model.mesh.getElementTypes()
        nodes, coord, parametricCoord = gmsh.model.mesh.getNodes()
        
        nodes = np.array(nodes, dtype=int) - 1 # node numbers
        Nn = nodes.shape[0] # Number of nodes

        # Organize nodes from smallest to largest
        sortedIdx = np.argsort(nodes)
        sortedNodes = nodes[sortedIdx]

        # Here we will detect jumps in node numbering
        # Example nodes = [0 1 2 3 4 5 6 8]
        
        # Here we will detect the jump between 6 and 8.
        # diff = [0 0 0 0 0 0 0 1]
        diff = sortedNodes - np.arange(Nn)
        jumpInNodes = np.max(diff) > 0 # detect if there is a jump in the nodes

        # Array that stores the changes        
        # For example below -> Changes = [0 1 2 3 4 5 6 0 7]
        # changes is used such correctedNodes = changes[nodes]
        changes = np.zeros(nodes.max()+1, dtype=int)        
        changes[sortedNodes] = sortedNodes - diff

        # The coordinate matrix of all nodes used in the mesh is constructed        
        coordo: np.ndarray = coord.reshape(-1,3)[sortedIdx,:]

        # Apply coef to scale coordinates
        coordo = coordo * coef

        knownDims = [] # known dimensions in the mesh
        # For each element type
        for gmshId in elementTypes:
                                        
            # Retrieves element numbers and connection matrix
            elementTags, nodeTags = gmsh.model.mesh.getElementsByType(gmshId)
            elementTags = np.array(elementTags, dtype=int) - 1 # tags for each elements
            nodeTags = np.array(nodeTags, dtype=int) - 1 # connection matrix in shape (e * nPe)

            nodeTags: np.ndarray = changes[nodeTags] # Apply changes to correct jumps in nodes
            
            # Elements
            Ne = elementTags.shape[0] # number of elements
            nPe = GroupElem_Factory.Get_ElemInFos(gmshId)[1] # nodes per element
            connect: np.ndarray = nodeTags.reshape(Ne, nPe) # Builds connect matrix

            # Nodes            
            nodes = np.unique(nodeTags) 
            Nmax = nodes.max() # Check that max node numbers can be reached in coordo
            assert Nmax <= (coordo.shape[0]-1), f"Nodes {Nmax} doesn't exist in coordo"

            # Element group creation
            groupElem = GroupElem_Factory.Create_GroupElem(gmshId, connect, coordo, nodes)
            
            # We add the element group to the dictionary containing all groups
            dict_groupElem[groupElem.elemType] = groupElem
            
            # Check that the mesh does not have a group of elements of this dimension
            if groupElem.dim in knownDims and groupElem.dim == meshDim:
                recoElement = 'Triangular' if meshDim == 2 else 'Tetrahedron'
                raise Exception(f"Importing the mesh is impossible because several {meshDim}D elements have been detected. Try out {recoElement} elements.\n You can also try standardizing the mesh size")
                # TODO make it work ?
                # Can be complicated especially in the creation of elemental matrices and assembly
                # Not impossible but not trivial
                # Relaunch the procedure if it doesn't work?
            knownDims.append(groupElem.dim)

            # Here we'll retrieve the nodes and elements belonging to a group
            physicalGroups = gmsh.model.getPhysicalGroups(groupElem.dim)
            # add nodes and elements associated with physical groups
            def __addPysicalGroup(group: tuple[int, int]):

                dim = group[0]
                tag = group[1]
                name = gmsh.model.getPhysicalName(dim, tag)

                nodeTags, __ = gmsh.model.mesh.getNodesForPhysicalGroup(dim, tag)
                    
                # If no node has been retrieved, move on to the nextPhysics group.
                if nodeTags.size == 0: return
                nodeTags = np.array(nodeTags, dtype=int) - 1

                # nodes associated with the group
                nodesGroup = changes[nodeTags] # Apply change

                # add the group for notes and elements
                groupElem.Set_Nodes_Tag(nodesGroup, name)
                groupElem.Set_Elements_Tag(nodesGroup, name)

            [__addPysicalGroup(group) for group in physicalGroups]
        
        tic.Tac("Mesh","Construct mesh object", self.__verbosity)

        gmsh.finalize()

        mesh = Mesh(dict_groupElem, self.__verbosity)

        return mesh
    
    @staticmethod
    def Construct_2D_meshes(L=10, h=10, taille=3) -> list[Mesh]:
        """2D mesh generation."""

        interfaceGmsh = Interface_Gmsh(openGmsh=False, verbosity=False)

        list_mesh2D = []
        
        domain = Domain(Point(0,0,0), Point(L, h, 0), meshSize=taille)
        line = Line(Point(x=0, y=h/2, isOpen=True), Point(x=L/2, y=h/2), meshSize=taille, isOpen=False)
        lineOpen = Line(Point(x=0, y=h/2, isOpen=True), Point(x=L/2, y=h/2), meshSize=taille, isOpen=True)
        circle = Circle(Point(x=L/2, y=h/2), L/3, meshSize=taille, isHollow=True)
        circleClose = Circle(Point(x=L/2, y=h/2), L/3, meshSize=taille, isHollow=False)

        aireDomain = L*h
        aireCircle = np.pi * (circleClose.diam/2)**2

        def testAire(aire):
            assert np.abs(aireDomain-aire)/aireDomain <= 1e-6, "Incorrect surface"

        # For each type of 2D element
        for t, elemType in enumerate(ElemType.get_2D()):

            print(elemType)

            mesh1 = interfaceGmsh.Mesh_2D(domain, elemType=elemType, isOrganised=False)
            testAire(mesh1.area)
            
            mesh2 = interfaceGmsh.Mesh_2D(domain, elemType=elemType, isOrganised=True)
            testAire(mesh2.area)

            mesh3 = interfaceGmsh.Mesh_2D(domain, [circle], elemType)
            # Here we don't check because there are too few elements to properly represent the hole

            mesh4 = interfaceGmsh.Mesh_2D(domain, [circleClose], elemType)
            testAire(mesh4.area)

            mesh5 = interfaceGmsh.Mesh_2D(domain, cracks=[line], elemType=elemType)
            testAire(mesh5.area)

            mesh6 = interfaceGmsh.Mesh_2D(domain, cracks=[lineOpen], elemType=elemType)
            testAire(mesh6.area)

            for m in [mesh1, mesh2, mesh3, mesh4, mesh5, mesh6]:
                list_mesh2D.append(m)
        
        return list_mesh2D

    @staticmethod
    def Construct_3D_meshes(L=130, h=13, b=13, taille=7.5, useImport3D=False):
        """3D mesh generation."""        

        domain = Domain(Point(y=-h/2,z=-b/2), Point(x=L, y=h/2,z=-b/2), meshSize=taille)
        circleCreux = Circle(Point(x=L/2, y=0,z=-b/2), h*0.7, meshSize=taille, isHollow=True)
        circle = Circle(Point(x=L/2, y=0 ,z=-b/2), h*0.7, meshSize=taille, isHollow=False)
        axis = Line(domain.pt1+[-1,0], domain.pt1+[-1,h])

        volume = L*h*b

        def testVolume(val):
            assert np.abs(volume-val)/volume <= 1e-6, "Incorrect volume"

        folder = Folder.Get_Path()        
        partPath = Folder.Join(folder,"3Dmodels","beam.stp")

        interfaceGmsh = Interface_Gmsh()

        list_mesh3D = []
        # For each type of 3D element
        for t, elemType in enumerate(ElemType.get_3D()):
            
            if useImport3D and elemType in ["TETRA4","TETRA10"]:
                meshPart = interfaceGmsh.Mesh_Import_part(partPath, 3, meshSize=taille, elemType=elemType)
                list_mesh3D.append(meshPart)

            mesh1 = interfaceGmsh.Mesh_3D(domain, [], [0,0,-b], [3], elemType=elemType)
            list_mesh3D.append(mesh1)
            testVolume(mesh1.volume)                

            mesh2 = interfaceGmsh.Mesh_3D(domain, [circleCreux], [0,0,-b], [3], elemType)
            list_mesh3D.append(mesh2)            

            mesh3 = interfaceGmsh.Mesh_3D(domain, [circle], [0,0,-b], [3], elemType)
            list_mesh3D.append(mesh3)
            testVolume(mesh3.volume)

        return list_mesh3D
    
    def Save_Simu(self, simu: _Simu, results: list[str]=[], details=False,
                  edgeColor='black', plotMesh=True, showAxes=False, folder: str=""):

        assert isinstance(results, list), 'results must be a list'
        
        self._init_gmsh()

        def getColor(c:str):
            """transform matplotlib color to rgb"""
            rgb = np.asarray(matplotlib.colors.to_rgb(edgeColor)) * 255
            rgb = np.asarray(rgb, dtype=int)
            return rgb

        def reshape(values: np.ndarray):
            """reshape values to get them at the corners of the elements"""
            values_n = np.reshape(values, (mesh.Nn, -1))
            values_e: np.ndarray = values_n[connect_e]
            if len(values_e.shape) == 3:
                values_e = np.transpose(values_e, (0,2,1))
            return values_e.reshape((mesh.Ne, -1))
        
        mesh = simu.mesh
        Ne = mesh.Ne
        nPe = mesh.groupElem.nbCorners # do this because it is not working for quadratic elements
        connect_e = mesh.connect[:,:nPe]
        elements_e = reshape(mesh.coordo)

        def types(elemType: str):
            """get gmsh type associated with elemType"""
            if 'POINT' in elemType:
                return 'P'
            elif 'SEG' in elemType:
                return 'L'
            elif 'TRI' in elemType:
                return 'T'
            elif 'QUAD' in elemType:
                return 'Q'
            elif 'TETRA' in elemType:
                return 'S'
            elif 'HEXA' in elemType:
                return 'H'
            elif 'PRISM' in elemType:
                return 'I'
            elif 'PYRA' in elemType:
                return 'Y'
        
        gmshType = types(mesh.elemType)
        colorElems = getColor(edgeColor)

        # get nodes and elements field to plot
        nodesField, elementsField = simu.Results_nodesField_elementsField()
        [results.append(result) for result in (nodesField + elementsField) if result not in results]

        dict_results: dict[str, list[np.ndarray]] = {result: [] for result in results}

        for i in range(simu.Niter):
            simu.Set_Iter(i)
            [dict_results[result].append(reshape(simu.Result(result))) for result in results]
            
        def AddView(name: str, values_e: np.ndarray):
            """Add a view"""

            if name == 'displacement_matrix_0':
                name='ux'
            elif name == 'displacement_matrix_1':
                name='uy'
            elif name == 'displacement_matrix_2':
                name='uz'                

            view = gmsh.view.add(name)
            
            gmsh.view.option.setNumber(view, "IntervalsType", 3)
            # (1: iso, 2: continuous, 3: discrete, 4: numeric)
            gmsh.view.option.setNumber(view, "NbIso", 10)

            if plotMesh:
                gmsh.view.option.setNumber(view, "ShowElement", 1)

            if showAxes:
                gmsh.view.option.setNumber(view, "Axes", 1)
                # (0: none, 1: simple axes, 2: box, 3: full grid, 4: open grid, 5: ruler)
            
            gmsh.view.option.setColor(view, 'Lines', *colorElems)
            gmsh.view.option.setColor(view, 'Triangles', *colorElems)
            gmsh.view.option.setColor(view, 'Quadrangles', *colorElems)
            gmsh.view.option.setColor(view, 'Tetrahedra', *colorElems)
            gmsh.view.option.setColor(view, 'Hexahedra', *colorElems)
            gmsh.view.option.setColor(view, 'Pyramids', *colorElems)
            gmsh.view.option.setColor(view, 'Prisms', *colorElems)

            # S for scalar, V for vector, T
            if values_e.shape[1] == nPe:
                vt = 'S'
            else:
                vt = 'S'

            res = np.concatenate((elements_e, values_e), 1)

            gmsh.view.addListData(view, vt+gmshType, Ne, res.reshape(-1))
            
            if folder != "":
                gmsh.view.write(view, Folder.Join(folder, "simu.pos"), True)

            return view

        for result in dict_results.keys():

            nIter = len(dict_results[result])

            if nIter == 0: continue

            dof_n = dict_results[result][0].shape[-1] // nPe

            vals_e_i_n = np.concatenate(dict_results[result], 1).reshape((Ne, nIter, dof_n, -1))

            if dof_n == 1:
                view = AddView(result, vals_e_i_n[:,:,0].reshape((Ne,-1)))
            else:
                views = [AddView(result+f'_{n}', vals_e_i_n[:,:,n].reshape(Ne,-1)) for n in range(dof_n)]

        # Launch the GUI to see the results:
        if '-nopopup' not in sys.argv and self.__openGmsh:
            gmsh.fltk.run()

        gmsh.finalize()