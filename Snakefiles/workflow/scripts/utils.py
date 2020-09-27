#! bin/bash 

import sys, os
import argparse 
import pandas as pd
import numpy as np

def is_unique(entries):
    a = entries.to_numpy()
    return (a[0] == a[1:]).all()

def check_x_and_y_single(entries, column):
    columns = column
    return_values = ['File accession_Accessibility bam']
    if not is_unique(entries[columns[0]]):
        return str(return_values[0]), str(return_values[1])
    else:
        return -1, -1

def check_x_and_y(entries, column):
    columns = column
    return_values = ['File accession_Accessibility bam', 'File accession_H3K27ac bam']
    # check for biological replicates
    if not is_unique(entries[columns[0]]):
        return str(return_values[0]), str(return_values[1])
    elif not is_unique(entries[columns[1]]):
        return str(return_values[1]), str(return_values[0])
    else:
        return -1, -1
    
# This function is used by grabUnique to treat all ambigiously paired bam files as singleend 
def findFilterFiles(outfile, outfile2):
    p = pd.read_csv(outfile, sep="\t", header=None)
    p2 = pd.read_csv(outfile2, sep="\t", header=None)

    common = p[0].loc[p[0].isin(p2[0])]
    remove_files_p2 = p2[0].loc[np.logical_not(p2[0].isin(list(common)))]
    remove_files_p2.to_csv(outfile2, sep="\t", header=False, index=False)

# This function grabs all unique entries in singleend and paireend lookup table for entry into removing duplicates function 
# It also resolves the conflict of bamfiles that are inaccurately labelled as both "pairedend" and "singleend" in ENCODE 
def grabUnique(outdir, filenames):
    for filename in filenames:
        data = pd.read_csv(os.path.join(outdir, filename), sep="\t", header=None)
        unique = data[0].drop_duplicates()
        unique.to_csv(os.path.join(outdir, "unique_"+str(filename)), sep="\t", index=False, header=False)
    # filter both files to ensure that each entry only appears once
    outfile = os.path.join(outdir, "unique_"+str(filenames[0]))
    outfile2 = os.path.join(outdir, "unique_"+str(filenames[1]))

    # find common entries
    findFilterFiles(outfile, outfile2)

def rename_bam_for_pairedend(metadata, col, paired):
    indicies = metadata['File accession_'+str(col)].loc[metadata['Run type_'+str(col)]==str(paired)].index.astype('int')
    metadata['File accession_'+str(col)+" bam"] = metadata['File accession_'+str(col)]
#    accessibility_col = metadata.columns.get_loc('File accession_'+str(col)+" bam")
    metadata.loc[indicies, 'File accession_'+str(col)+" bam"] = metadata.loc[indicies, 'File accession_'+str(col)+" bam"].astype('str') + ".nodup"
    return metadata
    
# This function prepares the lookup tables for input into ABC
# Where each DHS, H3K27ac bam file is appended to its corresponding celltype
def prepareLookup(args, metadata, title):
# for pairedend data accession files, change name to *.nodup.bam since duplicates need to be removed from these files
#    metadata_tmp = rename_bam_for_pairedend(metadata, 'Accessibility', "paired-ended") 
#    metadata = rename_bam_for_pairedend(metadata_tmp, 'H3K27ac', "paired-ended")
    # process biosample term name 
    metadata['Biosample term name'] = [str(i).replace(",", "").replace(" ", "_") for i in metadata['Biosample term name']]
    celltypes = metadata['Biosample term name'].drop_duplicates()
    celltypes.to_csv(os.path.join(args.outdir, "cells.txt"), sep="\t", header=False, index=False)
    metadata['File accession_Accessibility bam'] = metadata['File accession_Accessibility bam']+".bam"
    if args.h3k27ac is not None:
        metadata['File accession_H3K27ac bam'] = metadata['File accession_H3K27ac bam']+".bam"
        metadata[['Biosample term name', 'File accession_Accessibility bam', 'File accession_H3K27ac bam']].to_csv(os.path.join(args.outdir, str(title)+".tsv"), sep="\t", header=False, index=False)
        new_data = metadata.rename(index={key:value for key, value in zip(metadata.index, metadata['Biosample term name'])})
        new_data[['File accession_Accessibility bam', 'File accession_H3K27ac bam']].to_json(os.path.join(args.outdir, str(title)+".json"), orient='index')
    else:
        new_data = metadata.rename(index={key:value for key, value in zip(metadata.index, metadata['Biosample term name'])})
        new_data[['File accession_Accessibility bam']].to_json(os.path.join(args.outdir, str(title)+".json"), orient='index')
    return metadata

def mapExperimentToLength(dhs, dhs_fastq):
    dhs_lookup = dhs_fastq[['Experiment accession', 'Run type']].drop_duplicates()
    dhs_bam = dhs.loc[(dhs['File format']=='bam') & (dhs['Output type']=='unfiltered alignments')]
    paired_type = []
    for name in dhs_bam['Experiment accession']:
        matched = dhs_lookup['Run type'].loc[dhs_lookup['Experiment accession']==name]
        if len(matched) >1 :
            type_ = matched.values[0]
        else:
            type_ = "single-ended"
        paired_type.append(type_)
    dhs_bam['Run type'] = paired_type
    return dhs_bam
        

# This function updates the lookup table such that entries that have bamfiles with biological replicates undergo a merging process and the collective pooled bam is now updated in the table 
def getExperimentsCombined(args,metadata, biosample_entries):
    to_combine = {}
    df = metadata
    update_lookup = {}
    for biosample in list(biosample_entries):
        biosample_entry = metadata.loc[metadata['Biosample term name']==biosample]
        if len(biosample_entry) > 1:
            if args.h3k27ac is not None:
                col1, col2 = check_x_and_y(biosample_entry, column=['Biological replicate(s)_Accessibility', 'Biological replicate(s)_H3K27ac'])
            else:
                col1, _ = check_x_and_y(biosample_entry, column=['Biological replicate(s)_Accessibility'])
            if col1 != -1:
                index = list(biosample_entry.index.astype('int'))
                df.loc[index[0], col1] = str(biosample_entry.loc[index[0], col1]) + "_pooled"
                df = df.drop(index[1:])
                to_combine[str(biosample).replace(",", "").replace(" ", "_")] = list(set([str(entry)+".bam" for entry in biosample_entry.loc[:,col1]])) + [str(biosample_entry.loc[index[0], col1]) + "_pooled.bam"]
            else:
                index = list(biosample_entry.index.astype('int'))
                df = df.drop(index[1:])
    return to_combine, df

def save_metadata(args, duplicates): 
    duplicates.to_csv(os.path.join(args.outdir, "metadata.tsv"), sep="\t", index=False)
    # grab celltypes with biological replicates
    df_biological =  duplicates.loc[duplicates.duplicated(['Biosample term name'], keep=False)]
    df_biological.to_csv(os.path.join(args.outdir, "Replicates_metadata.tsv"), sep="\t", index=False)

# This function grabs the samples that have paired ends for paired end bam processing 
# It saves pairedend bams and singleend bams for removal of duplicates 
def obtainDuplicated(args, subset_intersected):
    duplicate_merge_columns = ['Biosample term name', 'Biosample organism', 'Biosample treatments','Biosample treatments amount', 'Biosample treatments duration','Biosample genetic modifications methods','Biosample genetic modifications categories','Biosample genetic modifications targets', 'Biosample genetic modifications gene targets', 'File assembly', 'Genome annotation', 'File format', 'File type', 'Output type', 'Lab', 'Biological replicate(s)_Accessibility']
    dhs_duplicates = subset_intersected[subset_intersected.duplicated(['Experiment accession_Accessibility'], keep=False)].drop_duplicates(duplicate_merge_columns)
    if args.h3k27ac is not None:
        h3k27acduplicates = subset_intersected[subset_intersected.duplicated(['Experiment accession_H3K27ac'], keep=False)].drop_duplicates(duplicate_merge_columns)
    
        comb_duplicates = pd.concat([dhs_duplicates, h3k27acduplicates])
        duplicates = comb_duplicates.drop_duplicates()
        duplicates = rename_bam_for_pairedend(duplicates, 'H3K27ac', "paired-ended")
    else: 
        duplicates = dhs_duplicates.drop_duplicates()
    save_metadata(args, duplicates)

    metadata_orig = duplicates.copy()
    # rename paired-end duplicates file
    duplicates = rename_bam_for_pairedend(duplicates, 'Accessibility', "paired-ended")
    df_biological =  duplicates.loc[duplicates.duplicated(['Biosample term name'], keep=False)]
    df_biological_rep = df_biological['Biosample term name'].drop_duplicates()

    to_combine, metadata_unique = getExperimentsCombined(args, duplicates, df_biological_rep)
    with open(os.path.join(args.outdir, "Experiments_ToCombine.txt.tmp"), "w") as f:
        for key, value in zip(to_combine.keys(), to_combine.values()):
            f.write(str(key))
            f.write("\t")
            f.write(str(list(value)))
            f.write("\n")
        f.close()
    
    return metadata_orig, metadata_unique

