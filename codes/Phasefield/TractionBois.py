import Interface_Gmsh
import Simulations
import Materials
import Affichage
import PostTraitement
from Geom import np, Point, Domain, Circle, PointsList
import Folder

plt = Affichage.plt
import pandas as pd


Affichage.Clear()

folder = Folder.New_File("TractionBois", results=True)

pathData = "/Users/matnoel/Library/CloudStorage/OneDrive-Personal/__Doctorat/Essais/TractionBois/data.xlsx"

df = pd.read_excel(pathData)

forces = df["Force"].values #N
displacements = df["Dep"].values #mm

filtre = displacements < 0.05

forces = forces[filtre]
displacements = displacements[filtre]

plt.figure()
plt.plot(displacements, forces)

L = 105
H = 70

h = H/2

r3 = 3

epFissure = 0.5
lFissure = 20
a = 20
c = 20

d1 = 25.68
d2 = 40.85

alpha1 = 2.5 * np.pi/180
alpha2 = 20 * np.pi/180
alpha3 = 34 * np.pi/180

betha = (np.pi - alpha3 - (np.pi/2-alpha1))/2
d = r3/np.tan(betha)

l0 = H/100
tailleFin = l0/1
tailleGros = l0*5

p0 = Point(x=0, y=-epFissure/2)
p1 = Point(x=0, y=-h)
p2 = Point(x=a, y=-h)
p3 = Point(x=a+(d1+d)*np.sin(alpha1), y=-h+(d1+d)*np.cos(alpha1), r=r3)
p4 = Point(x=L-c-d2*np.cos(alpha2), y=-h+d2*np.sin(alpha2))
p5 = Point(x=L-c, y=-h)
p6 = Point(x=L, y=-h)
p7 = Point(x=L, y=h)
p8 = Point(x=L-c, y=h)
p9 = Point(x=L-c-d2*np.cos(alpha2), y=h-d2*np.sin(alpha2))
p10 = Point(x=a+(d1+d)*np.sin(alpha1), y=h-(d1+d)*np.cos(alpha1), r=r3)
p11 = Point(x=a, y=h)
p12 = Point(x=0, y=h)
p13 = Point(x=0, y=epFissure/2)
p14 = Point(x=lFissure, y=epFissure/2, r=epFissure/2)
p15 = Point(x=lFissure, y=-epFissure/2, r=epFissure/2)

listPoint = [p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14, p15]

points = PointsList(listPoint, tailleGros)

diam = 5
r = diam/2
c1 = Circle(Point(a/2, -h+7.5), diam, tailleFin, isCreux=True)
c2 = Circle(Point(L-c/2, -h+7.5), diam, tailleFin, isCreux=True)
c3 = Circle(Point(L-c/2, h-7.5), diam, tailleFin, isCreux=True)
c4 = Circle(Point(a/2, h-7.5), diam, tailleFin, isCreux=True)

geomObjectsInDomain = [c1, c2, c3, c4]

# fig, ax = plt.subplots()
# [ax.scatter(point.x, point.y, label=p) for p, point in enumerate(listPoint)]
# ax.autoscale()
# ax.legend()
# plt.show()


interface = Interface_Gmsh.Interface_Gmsh(False, False)

zone = 10
refineDomain = Domain(Point(lFissure-zone, -zone), Point(L, zone), meshSize=tailleFin)
mesh = interface.Mesh_Points_2D(points, refineGeom=refineDomain, inclusions=geomObjectsInDomain, elemType="TRI3")

# Affichage.Plot_Mesh(mesh)
Affichage.Plot_Model(mesh)
# plt.show()


# MATERIAU

# El=11580*1e6
# Gc = 300*1e6 # J/mm2
Gc = 1*1e-1 # J/mm2
El=12000
# Et=500
Et=500*3
Gl=450
vl=0.02
vt=0.44
v=0
comportement = Materials.Elas_IsotTrans(2, El=El, Et=Et, Gl=Gl, vl=vl, vt=vt, contraintesPlanes=True, epaisseur=12.5, axis_l=np.array([1,0,0]), axis_t=np.array([0,1,0]))

splits = Materials.PhaseField_Model.SplitType
reg = Materials.PhaseField_Model.RegularizationType

pfm = Materials.PhaseField_Model(comportement, splits.Zhang, reg.AT2, Gc, l0)

simu = Simulations.Simu_PhaseField(mesh, pfm, verbosity=False)

noeudsHaut = mesh.Nodes_Tag(["L35","L34"])
noeudsBas = mesh.Nodes_Tag(["L20","L21"])

noeudsBord = mesh.Nodes_Tag([f"L{i}" for i in np.arange(1, 16)])
# Affichage.Plot_Nodes(mesh, noeudsBord)

def Chargement(force: float):
    simu.Bc_Init()

    SIG = force/(np.pi*r**2/2)

    # simu.add_dirichlet(noeudsBas, [0,0], ["x","y"])
    
    simu.add_dirichlet(noeudsBas, [0], ["y"])
    simu.add_dirichlet(mesh.Nodes_Tag(["P26"]), [0], ["x"])

    # # simu.add_dirichlet(noeudsBas, [0], ["x"])
    # simu.add_surfLoad(noeudsBas, [lambda x,y,z: -SIG*(y-c4.center.y)/r * np.abs((y-c4.center.y)/r)], ["y"])

    simu.add_surfLoad(noeudsHaut, [lambda x,y,z: SIG*(y-c4.center.y)/r * np.abs((y-c4.center.y)/r)], ["y"])

    # simu.add_surfLoad(noeudsHaut, [lambda x,y,z: SIG*(y-c4.center.y)/r * np.abs((y-c4.center.y)/r)], ["y"])
    # simu.add_surfLoad(noeudsBas, [lambda x,y,z: -SIG*(y-c4.center.y)/r * np.abs((y-c4.center.y)/r)], ["y"])

Chargement(0)

Affichage.Plot_BoundaryConditions(simu)
# plt.show()

fig_Damage, ax_Damage, cb_Damage = Affichage.Plot_Result(simu, "damage")

# for iter, force, dep in zip(range(len(forces)), forces, displacements):
nf = 70*2
for iter, force in enumerate(np.linspace(0, 30, nf)):

    Chargement(force)

    simu.Solve(1e-0)

    simu.Save_Iteration()

    depNum = np.max(simu.displacement[noeudsHaut])

    # ecart = np.abs(depNum-dep)/dep
    # print(ecart)

    # Affichage.Plot_Result(simu, "Syy")
    # plt.show()

    pourcent = iter/len(forces)

    simu.Resultats_Set_Resume_Iteration(iter, force, "N", pourcent, True)

    cb_Damage.remove()
    fig_Damage, ax_Damage, cb_Damage = Affichage.Plot_Result(simu, "damage", ax=ax_Damage)
    plt.pause(1e-12)

    if np.max(simu.damage[noeudsBord]) >= 0.95:
        break

PostTraitement.Make_Paraview(folder, simu)