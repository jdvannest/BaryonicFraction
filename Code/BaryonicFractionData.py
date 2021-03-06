import argparse,pickle,pymp,pynbody,sys,warnings
import numpy as np
def myprint(string,clear=False):
    if clear:
        sys.stdout.write("\033[F")
        sys.stdout.write("\033[K") 
    print(string)
warnings.filterwarnings("ignore")
parser = argparse.ArgumentParser()
parser.add_argument("-s","--simulation",choices=['cptmarvel','elektra','storm','rogue'],required=True)
parser.add_argument("-t","--timestep",required=True)
parser.add_argument("-n","--numproc",required=True,type=int)
args = parser.parse_args()

#Verify that data file exists, and that the timestep hasn't already been calculated
try:
    Data = pickle.load(open('DataFiles/BaryonicFractionData.pickle','rb'))
except:
    print('Please initiate Data File')
    sys.exit()
    
if args.timestep in Data[args.simulation].keys(): 
    print(f'\tTimestep {args.simulation}-00{args.timestep} already complete.')
    sys.exit()

#Verify that simulation step is readable/exists
simpath = f'/myhome2/users/munshi/dwarf_volumes/{args.simulation}.cosmo25cmb.4096g5HbwK1BH/{args.simulation}.cosmo25cmb.4096g5HbwK1BH.00{args.timestep}/{args.simulation}.cosmo25cmb.4096g5HbwK1BH.00{args.timestep}'
try:
    with open(simpath+'.M200.amiga.stat') as f:
        stat = f.readlines()
        del stat[0]
except:
    print(f'\tTimestep {args.simulation}-00{args.timestep} has no stat file.')
    sys.exit()

Data[args.simulation][args.timestep] = {'time':np.nan,'halos':{}}
resolved = []
for line in stat:
    grp = int(line.split()[0])
    ngas = int(line.split()[2])
    nstar = int(line.split()[3])
    if ngas > 0:
        resolved.append(grp)
        Data[args.simulation][args.timestep]['halos'][str(grp)] = {'Rvir':float(line.split()[6]),
                                                                    'Mvir':float(line.split()[5]),
                                                                    'Mgas':float(line.split()[7]),
                                                                    'Mstar':float(line.split()[8])}
print(f'\t{len(resolved)} resolved halos to analyze.\n\tLoading {args.simulation}-00{args.timestep}...')

s = pynbody.load(simpath)
s.physical_units()
h = s.halos()
Data[args.simulation][args.timestep]['time'] = s.properties['time'].in_units('Gyr')
InnerData = pymp.shared.dict()
prog=pymp.shared.array((1,),dtype=int)
myprint(f'\t{args.simulation}-00{args.timestep} Loaded.',clear=True)
print('\tWriting: 0.00%')

with pymp.Parallel(args.numproc) as pl:
    for i in pl.xrange(len(resolved)):
        halo = h[resolved[i]]
        current = {'Mvir':np.nan,'Mstar':np.nan,'Mgas':np.nan,'MHI_Inner':np.nan,'MHI':sum(halo.g['HI']*halo.g['mass'])}

        try:
            pynbody.analysis.halo.center(halo)
            Rvir = Data[args.simulation][args.timestep]['halos'][str(resolved[i])]['Rvir']
            sphere = pynbody.filt.Sphere(.1*Rvir,(0,0,0))
            current['Mvir'] = halo[sphere]['mass'].sum()
            current['Mgas'] = halo.g[sphere]['mass'].sum()
            current['Mstar'] = halo.s[sphere]['mass'].sum()
            current['MHI_Inner'] = sum(halo.g[sphere]['HI']*halo.g[sphere]['mass'])
        except:
            pass

        prog[0]+=1
        myprint(f'\tWriting {round(prog[0]/len(resolved)*100,2)}%',clear=True)
        InnerData[str(resolved[i])] = current
        del current

for halo in resolved:
    Data[args.simulation][args.timestep]['halos'][str(halo)]['Mvir_Inner'] = InnerData[str(halo)]['Mvir']
    Data[args.simulation][args.timestep]['halos'][str(halo)]['Mgas_Inner'] = InnerData[str(halo)]['Mgas']
    Data[args.simulation][args.timestep]['halos'][str(halo)]['Mstar_Inner'] = InnerData[str(halo)]['Mstar']
    Data[args.simulation][args.timestep]['halos'][str(halo)]['MHI_Inner'] = InnerData[str(halo)]['MHI_Inner']
    Data[args.simulation][args.timestep]['halos'][str(halo)]['MHI'] = InnerData[str(halo)]['MHI']

out = open('DataFiles/BaryonicFractionData.pickle','wb')
pickle.dump(Data,out)
out.close()
myprint(f'\tData File Updated with {args.simulation}-00{args.timestep}',clear=True)