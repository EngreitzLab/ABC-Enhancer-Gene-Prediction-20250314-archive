import numpy as np
import sys, traceback
import pandas
from scipy import stats
import argparse
import glob
import os
from hic import *

#To do: 
#1. Use MLE to estimate exponent?

def parseargs():
    class formatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
        pass

    epilog = ("")
    parser = argparse.ArgumentParser(description='Helper to compute hic power-law fit parameters',
                                     epilog=epilog,
                                     formatter_class=formatter)
    readable = argparse.FileType('r')
    parser.add_argument('--hicDir', help="Directory containing bedgraphs. All files named *chr*.bg.gz will be loaded")
    parser.add_argument('--outDir', help="Output directory")
    parser.add_argument('--resolution', default=5000, type=int, help="Resolution of hic dataset (in bp)")
    parser.add_argument('--minWindow', default=10000, type=int, help="Minimum distance from gene TSS to compute normalizations (bp)")
    parser.add_argument('--maxWindow', default=1000000, type=int, help="Maximum distance from gene TSS to use to compute normalizations (bp)")

    args = parser.parse_args()
    return(args)

def main():
    args = parseargs()
    os.makedirs(args.outDir, exist_ok=True)

    #Juicebox format
    if True or hic_type == 'juicebox':
        HiC = load_hic_juicebox(args)
    elif hic_type == 'bedpe':
        HiC = load_hic_bedpe(args)

    #Run 
    slope, intercept = do_powerlaw_fit(HiC)

    #print
    res = pandas.DataFrame({'resolution' : [args.resolution], 'maxWindow' : [args.maxWindow], 'minWindow' : [args.minWindow] ,'pl_gamma' : [slope], 'pl_scale' : [intercept] })
    res.to_csv(os.path.join(args.outDir, 'hic.powerlaw.txt'), sep='\t', index=False, header=True)

def load_hic_juicebox(args):
    file_list = glob.glob(os.path.join(args.hicDir,'chr*/*.KRobserved'))

    all_data_list = []
    for this_file in file_list:
        try:
            print("Working on {}".format(this_file))
            this_data = load_hic(hic_file = this_file, hic_type = 'juicebox', hic_resolution = args.resolution, tss_hic_contribution = 100, window = args.maxWindow, min_window = args.minWindow)
            this_data['dist_for_fit'] = abs(this_data['bin1'] - this_data['bin2'])
            all_data_list.append(this_data)
        except Exception as e:
            print(e)
            traceback.print_exc(file=sys.stdout)

    all_data = pd.concat(all_data_list)

    return(all_data)

def load_bedpe():
    pass

def do_powerlaw_fit(HiC):
    print("Running regression")

    #TO DO:
    #Print out mean/var plot of powerlaw relationship
    HiC_summary = HiC.groupby('dist_for_fit').agg({'hic_kr' : 'sum'})
    HiC_summary['hic_kr'] = HiC_summary.hic_kr / HiC_summary.hic_kr.sum() #technically this normalization should be over the entire genome (not just to maxWindow). Will only affect intersept though..
    res = stats.linregress(np.log(HiC_summary.index), np.log(HiC_summary['hic_kr']))

    return res.slope, res.intercept

if __name__ == '__main__':
    main()