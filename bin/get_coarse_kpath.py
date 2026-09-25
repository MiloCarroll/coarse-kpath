#!/usr/bin/env python

import numpy as np
from argparse import ArgumentParser
import os
import shutil

parser = ArgumentParser()
parser.add_argument("numpoints",type=int)
parser.add_argument("-f","--folder",default='./')
parser.add_argument("-s","--splits",default=1)
parser.add_argument("-j","--setupjob",action="store_true")

args = parser.parse_args()

path = args.folder
if path[-1] != '/': path += '/'
target_n_kpoints = args.numpoints
splits = int(args.splits)
setupjob = args.setupjob

with open(path+'KPOINTS_band', 'r') as f:
    high_sym_kpoints = []
    rest_of_path = []
    irreducible_kpoints = []
    path_position = 0
    for i, line in enumerate(f):
        if i>2:
            l = line.replace('\n','').split(' ')
            while '' in l: l.remove('')
            if l[3] == '1':
                irreducible_kpoints.append(l)
            elif l[3] == '0':
                if len(l) == 5:
                    high_sym_kpoints.append(l)
                    path_position += 1
                else:
                    rest_of_path.append([path_position, l])
            else:
                print(f"hmmmmmm {l}")
        elif i==0:
            line1 = [line.replace('\n','')]
        elif i==2:
            line3 = [line.replace('\n','')]

reducible_kpoints_per_split = int(target_n_kpoints / splits) - len(irreducible_kpoints)
total_reducible_low_sym_kpoints = (reducible_kpoints_per_split * splits) - len(high_sym_kpoints)
print(total_reducible_low_sym_kpoints)
indexes = np.round(np.linspace(0, len(rest_of_path) - 1, total_reducible_low_sym_kpoints)).astype(int)

all_reducible_kpoints = []

for i in range(1,len(high_sym_kpoints)+1):
    all_reducible_kpoints.append(high_sym_kpoints[i-1])
    for j, kpoint in enumerate(rest_of_path):
        if kpoint[0] == i and j in indexes:
            all_reducible_kpoints.append(kpoint[1])

for split in range(splits):
    newline1 = ''
    new_file_lines = [line1, [0], line3]

    for kpoint in irreducible_kpoints:
        new_file_lines.append(kpoint)

    for i in range(reducible_kpoints_per_split):
        kpoint_to_add = all_reducible_kpoints.pop(0)
        new_file_lines.append(kpoint_to_add)
        if len(kpoint_to_add) == 5:
            newline1 = newline1 + kpoint_to_add[4] + ' -> '
        
    newline1 = newline1[:-4]

    new_file_lines[0] = [newline1]
    new_file_lines[1] = [str(len(new_file_lines)-3)]

    os.mkdir(f'split-{str(split+1).zfill(3)}')

    splitdir = path + f'split-{str(split+1).zfill(3)}/'

    with open(splitdir + 'KPOINTS', 'w') as f:
        for l in new_file_lines:
            f.write(" ".join(l)+'\n')
    
    if setupjob:
        for f in ['job.sh','INCAR','POSCAR','POTCAR']:
            try:
                shutil.copy(f,splitdir + f)
            except FileNotFoundError as e:
                print(f"Cannot find {f}:\n{e}")

    print(f"split-{str(split+1).zfill(3)}: {len(new_file_lines)-3} points")