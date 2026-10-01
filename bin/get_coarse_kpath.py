#!/usr/bin/env python

import numpy as np
from argparse import ArgumentParser
from os import mkdir
from shutil import copy
from math import ceil

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("minpoints", type=int, description='minimum number of reducible k-points to be included in coarse path.')
    parser.add_argument("--pps", '--pointspersplit', type=int, description='number of k-points per split.')
    parser.add_argument("-f", "--file", default='KPOINTS_band', description='name of full k-path file (defaults to KPOINTS_band).')
    parser.add_argument("-j", "--setupjob", action="store_true", description='set up VASP job in split folders. requires POSCAR, POTCAR, INCAR, and job.sh files.')

    args = parser.parse_args()

    return (args.minpoints, 
            args.pointspersplit,
            args.kpoints_file,
            args.setupjob,
    )


def read_full_kpoints(kpoint_file_path):
    kpoints = {'irreducible':[],
               'reducible':[],
               'high_sym':[]}
    try:
        with open(kpoint_file_path, 'r') as f:
            path_position = 0
            for i, line in enumerate(f):
                if i>2:
                    l = line.replace('\n','').split(' ')
                    while '' in l: l.remove('')
                    if l[3] == '1':
                        kpoints['irreducible'].append(l)
                    elif l[3] == '0':
                        if len(l) == 5:
                            kpoints['high_sym'].append(l)
                            path_position += 1
                        else:
                            kpoints['reducible'].append([path_position, l])
                    else:
                        print(f'Cannot identify kpoint "{l}"')
        return kpoints
    except FileNotFoundError as e: 
        print(f'FileNotFoundError!\n{e}')
        exit()


def decide_n_splits(kpoints, min_points, points_per_split):
    n_irreducible = len(kpoints['irreducible'])
    n_reducible = len(kpoints['reducible'] + len(kpoints['high_sym']))

    if min_points > n_reducible:
        print(f"ERROR: more requested reducible k-points ({str(min_points)}) than in whole path file ({str(n_reducible)}). Exiting.")
        exit()
    elif min_points == n_reducible:
        print(f"ERROR: requested as many reducible k-points as in whole path file ({str(n_reducible)}). Exiting.")
        exit()

    if n_irreducible > points_per_split:
        print(f"ERROR: --pointspersplit ({str(points_per_split)}) is fewer than number of irreducible points ({str(n_irreducible)}). Exiting.")
        exit()
    elif  n_irreducible > points_per_split / 2:
        print(f"WARNING: --pointspersplit ({str(points_per_split)}) is not much larger than number of irreducible points ({str(n_irreducible)}). Consider raising --pps to improve efficiency.")

    reducible_points_per_split = points_per_split - n_irreducible
    n_splits = ceil(min_points / reducible_points_per_split)

    if n_splits * reducible_points_per_split > n_reducible:
        print(f"ERROR: more calculated reducible k-points ({str(n_splits * reducible_points_per_split)}) than in whole path file ({str(n_reducible)}). Consider lowering --minpoints. Exiting.")
        exit()

    return n_splits, reducible_points_per_split


def split_up_kpoints(kpoints, n_splits, points_per_split):

    reducible_points_per_split = points_per_split - len(kpoints['irreducible'])
    total_reducible_low_sym_points = (reducible_points_per_split * n_splits) - len(kpoints['high_sym'])

    indexes = np.round(np.linspace(0, len(kpoints['reducible']) - 1, total_reducible_low_sym_points)).astype(int)

    all_reducible_kpoints = []

    for i in range(1,len(kpoints['high_sym'])+1):
        all_reducible_kpoints.append(kpoints['high_sym'][i-1])
        for j, kpoint in enumerate(kpoints['reducible']):
            if kpoint[0] == i and j in indexes:
                all_reducible_kpoints.append(kpoint[1])

    split_points = []

    for i in range(n_splits):
        single_split = []
        for kpoint in kpoints['irreducible']:
            single_split.append(kpoint)
        for j in range(reducible_points_per_split):
            kpoint_to_add = all_reducible_kpoints.pop(0)
            single_split.append(kpoint_to_add)
        split_points.append(single_split)
    return split_points


def write_kpoints_in_split_folder(points, split_number, set_up_job=False):
        splitdir = f'split-{str(split_number).zfill(3)}/'
        try:
            mkdir(splitdir)
        except FileExistsError:
            pass

        line1 = ''
        for p in points:
            if len(p) == 5:
                line1 += p[4] + ' -> '
        line1 = line1[:-4]
        line2 = str(len(points))
        line3 = 'Reciprocal'

        new_file_lines = [line1, line2, line3] + points

        with open(splitdir + 'KPOINTS', 'w') as f:
            for l in new_file_lines:
                f.write(" ".join(l)+'\n')
        
        if set_up_job:
            for f in ['job.sh','INCAR','POSCAR','POTCAR']:
                try:
                    copy(f, splitdir)
                except FileNotFoundError as e:
                    print(f"Could not find file '{f}' when setting up job.")


def main():
    min_points, points_per_split, kpoints_file, set_up_job = parse_args()
    kpoints = read_full_kpoints(kpoints_file)
    n_splits, reducible_points_per_split = decide_n_splits(kpoints, min_points, points_per_split)
    split_points = split_up_kpoints(kpoints, n_splits, points_per_split)
    for i,kps in enumerate(split_points):
        write_kpoints_in_split_folder(kps, i+1, set_up_job)
    print(f"wrote {n_splits} split folders, with {str(len(split_points[0]))} k-points each, for a total of {str(reducible_points_per_split * n_splits)} symmetry-reducible k-points in the path.")