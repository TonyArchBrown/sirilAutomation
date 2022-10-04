import sys
import os
import getopt
from datetime import datetime
from pysiril.siril import *
from pysiril.wrapper import *
from pysiril.addons import * 

def set_defaults():
    global arg_workingdir
    global arg_masterbiasfile
    global arg_sequencestart
    global arg_targetname
    global arg_process
    global arg_filterfwhm
    global arg_filterround
    global arg_filterwfwhm
    global arg_cpus

    # Set default args
    arg_workingdir = os.getcwd()
    arg_sequencestart = 1
    arg_masterbiasfile = ""
    arg_targetname = ""
    arg_process = "stack"
    arg_filterfwhm = 10
    arg_filterround = 0.1
    arg_filterwfwhm = 30
    arg_cpus = 4


def init(argv):
    arg_help = "{0} -d <base directory> -s <sequence start number> -b <master bias location> -t <target name> -p <process (reg, stack, preproc)) -f <Filter FWHM> -w <Filter wFWHM> -r <Filter Roundness (0-1)> ".format(argv[0])
    
    # Set the defaults
    set_defaults()

    try:
        opts, args = getopt.getopt(argv[1:], "hd:s:b:t:p:f:w:r:c:", ["help", "basedir=", 
        "sequencestart=", "masterbiasfile=", "targetname=", "process=", 
        "filterfwhm=", "filterwfwhm=", "filterround=", "cpu=" ])
        # Minimum number of arguments are bias location and target name - all others can de defaulted
        if len(opts)<2:
            print(arg_help)  # print the help message
            sys.exit(3)
    except:
        print(arg_help)
        sys.exit(2)
    
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(arg_help)  # print the help message
            sys.exit(2)
        elif opt in ("-d", "--basedir"):
            global arg_workingdir
            arg_workingdir = arg
        elif opt in ("-s", "--sequencestart"):
            global arg_sequencestart
            arg_sequencestart = arg
        elif opt in ("-b", "--masterbiasfile"):
            global arg_masterbiasfile
            arg_masterbiasfile = arg
        elif opt in ("-t", "--targetname"):
            global arg_targetname
            arg_targetname = arg
        elif opt in ("-p", "--process"):
            global arg_process
            if arg.upper() in ("REG", "R"):
                arg_process = "reg"
            elif arg.upper() in ("STACK", "S"):
                arg_process = "stack"
            elif arg.upper() in ("PREPROC", "P"):
                arg_process = "preproc"
            else:
                print(arg_help)  # print the help message
                sys.exit(2)
        elif opt in ("-f","--filterfwhm"):
            global arg_filterfwhm
            arg_filterfwhm=arg
        elif opt in ("-r","--filterround"):
            global arg_filterround
            arg_filterround=arg
        elif opt in ("-w","--filterwfwhm"):
            global arg_filterwfwhm
            arg_filterwfwhm=arg
        elif opt in ("-c","--cpu"):
            global arg_cpus
            arg_cpus=arg
    

def count_files(dir):
    fct=Addons(app)
    return fct.GetNbFiles(os.path.join(dir, '*.cr2'))

# NOTE - Sigma low and High are set here for Flats
def master_flat(flat_dir, bias_file, seq_start, process_dir):
    cmd.cd(flat_dir)
    cmd.convertraw( 'flat', out=process_dir, start=seq_start )
    cmd.cd( process_dir )
    cmd.preprocess( 'flat', bias=bias_file )
    cmd.stack( 'pp_flat', type='rej', sigma_low=3.0, sigma_high=3.0, norm='mul')

# NOTE - Sigma low and High are set here for Darks
def master_dark(dark_dir, bias_file, seq_start, process_dir):
    cmd.cd(dark_dir)
    cmd.convertraw( 'dark', out=process_dir, start=seq_start )
    cmd.cd( process_dir )
    cmd.preprocess( 'dark', bias=bias_file )
    cmd.stack( 'pp_dark', type='rej', sigma_low=3.5, sigma_high=3.5, norm='no')

def pre_process_lights(light_dir, bias_file, seq_start, process_dir):
    cmd.cd(light_dir)
    cmd.convertraw( 'light', out=process_dir, start=seq_start )
    cmd.cd( process_dir )
    # Dark Optimised with hot pixel cosmetic correction of sigma 3, no cold.
    cmd.preprocess( 'light', bias=bias_file, flat='pp_flat_stacked', 
                    dark='pp_dark_stacked', debayer=True, 
                    opt=True, cfa=True, equalize_cfa=True)

# Need to set a reference image as default will select the first, if this is rubbish (no or few stars)
# then fails.
# TO DO - when 2pass is provided then run as it is possible if the first image is poor then reference
# for the registration will be poor
def register_lights():    
    cmd.register( 'pp_light' )

## Stack using filters to attempt to throw away bad frames.
## Roundness, FWHM and wFWHM are all used.
def stack_lights(process_dir, filterFWHM, filterWFWHM, filterRound):
    # Create a nice filename
    outputFilename = 'stacked_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.fit'

    cmd.cd( process_dir )
    cmd.stack('r_pp_light', type='rej', sigma_low=3, sigma_high=3, 
                norm='addscale', output_norm=False, 
                filter_round=filterRound, filter_fwhm=filterFWHM, filter_wfwhm=filterWFWHM,
                out=outputFilename)

def process():
    # Define globals
    global app
    global cmd

    init(sys.argv)
 
# Starting and preparing pySiril
    app = Siril()
 
    try:
        cmd = Wrapper(app)
        
        # Turn on or off (True or False) the Siril verbose output
        app.MuteSiril(False)
        app.Open()

        # Set preferences
        cmd.set32bits()
        cmd.setext('fit')
        cmd.setcpu(int(arg_cpus))
        
        # Define the file paths from the globals
        processDir=os.path.join(arg_workingdir, 'process')
        sourceFlatDir=os.path.join(arg_workingdir, 'FLAT')
        sourceDarkDir=os.path.join(arg_workingdir, 'DARK')
        sourceLightDir=os.path.join(arg_workingdir,'LIGHT', arg_targetname)
     
        indexStart=int(arg_sequencestart)
        print('*****************************************')
        print('Processing Started at ' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        print('*****************************************')
        print('  DIRECTORIES: -')
        print('    Working Directory = ' + arg_workingdir)
        print('    Bias Master File = ' + arg_masterbiasfile)
        print('    Light Directory = ' + sourceLightDir)
        print('    Flat Directory = ' + sourceFlatDir)
        print('    Dark Directory = ' + sourceDarkDir)
        print('    Process Directory = ' + processDir)
        print('\n  Options: -')
        print('    Index Start = ' + str(indexStart))
        print('    CPUs to use = ' + arg_cpus)
        print('    Process Stack = ' + arg_process)
        if arg_process=="stack":
            print('      Filter FWHM = ' + str(arg_filterfwhm))
            print('      Filter wFWHM = ' + str(arg_filterwfwhm))
            print('      Filter Roundness = ' + str(arg_filterround))
        print('*****************************************')

        # Prepare Master frames
        fileCount = count_files(sourceFlatDir)
        print ('Processing ' + str(fileCount) + ' flats')
        master_flat(sourceFlatDir, arg_masterbiasfile, indexStart, processDir)
        
        fileCount = count_files(sourceDarkDir)
        print ('Processing ' + str(fileCount) + ' darks')
        master_dark(sourceDarkDir, arg_masterbiasfile, indexStart, processDir)
        
        # Dark optimisation and debayering is performed here
        fileCount = count_files(sourceLightDir)
        print ('Processing ' + str(fileCount) + ' lights')
        pre_process_lights(sourceLightDir, arg_masterbiasfile, indexStart, processDir)

        # If requested automatically stack all registered Lights
        if arg_process in ("stack", "reg"):
            register_lights()

        # If requested automatically stack all registered Lights
        if arg_process == "stack":
            stack_lights(processDir, arg_filterfwhm, arg_filterwfwhm, arg_filterround)
       
        print('*****************************************')
        print('Processing Completed at ' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        print('*****************************************')
     
    except Exception as e :
        print("\n*** !!!ERROR!!! *** " + str(e) + "\n" )

    # Close Siril and remove instance
    app.Close()
    del app

    # MAIN - Kick off the program
if __name__ == "__main__":
    process()
