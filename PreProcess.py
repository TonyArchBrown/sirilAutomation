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
    global arg_masterdarkfile
    global arg_sequencestart
    global arg_targetname
    global arg_process
    global arg_filterfwhm
    global arg_filterround
    global arg_filterwfwhm
    global arg_cpus
    global arg_camera

    # Set default args
    arg_workingdir = os.getcwd()
    arg_sequencestart = 1
    arg_masterbiasfile = ""
    arg_targetname = ""
    arg_process = "stack"
    arg_cpus = 4
    arg_camera = "CANON_DSLR"

    # Default filters used that in effect turn off filtering
    arg_filterfwhm = 10
    arg_filterround = 0.1
    arg_filterwfwhm = 30
    
def init(argv):
    arg_help = "{0} -i <Camera (CANON_DSLR / ZWO_OSC)> -d <base directory> -s <sequence start number> -a <master dark file> -b <master bias(offset) file> -t <target name> -p <process (reg, stack, preproc)) -f <Filter FWHM> -w <Filter wFWHM> -r <Filter Roundness (0-1)> ".format(argv[0])
    
    # Set the defaults
    set_defaults()

    try:
        opts, args = getopt.getopt(argv[1:], "hi:d:s:a:b:t:p:f:w:r:c:", ["help", "camera=", "basedir=", 
        "sequencestart=", "masterdarkfile=", "masterbiasfile=", "targetname=", "process=", 
        "filterfwhm=", "filterwfwhm=", "filterround=", "cpu=" ])
        # Minimum number of arguments are bias or dark location and target name - all others can de defaulted
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
        if opt in ("-i", "--camera"):
            global arg_camera
            arg_camera = arg.upper()
        elif opt in ("-d", "--basedir"):
            global arg_workingdir
            arg_workingdir = arg
        elif opt in ("-s", "--sequencestart"):
            global arg_sequencestart
            arg_sequencestart = arg
        elif opt in ("-a", "--masterdarkfile"):
            global arg_masterdarkfile
            arg_masterdarkfile = arg
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
    
# Counts files in a given directory, camera is passed in for extension selection
def count_files(camera,dir):
    fct=Addons(app)
    if (camera=="CANON_DSLR"):
        return fct.GetNbFiles(os.path.join(dir, '*.cr2'))
    elif (camera=="ZWO_OSC"):
        return fct.GetNbFiles(os.path.join(dir, '*.fit')) + fct.GetNbFiles(os.path.join(dir, '*.fits'))

# NOTE - Sigma low and High are set here for Offset file (Bias for DSLR / DarkFlat for ZWO)
def master_offset(camera, offset_dir, seq_start, process_dir):
    cmd.cd(offset_dir)
    if(camera=="ZWO_OSC"):
        cmd.convert( 'offset', out=process_dir, start=seq_start )
    else:
        cmd.convertraw( 'offset', out=process_dir, start=seq_start )
    cmd.cd( process_dir )
    cmd.seqstat('offset','offset.csv', option='main')
    cmd.stack( 'offset', type='rej', sigma_low=3.0, sigma_high=3.0, out='master_offset.fit' )

# NOTE - Sigma low and High are set here for Flats
def master_flat(camera, flat_dir, offset_file, seq_start, process_dir):
    cmd.cd(flat_dir)
    if(camera=="ZWO_OSC"):
        cmd.convert( 'flat', out=process_dir, start=seq_start )
    else:
        cmd.convertraw( 'flat', out=process_dir, start=seq_start )
    cmd.cd( process_dir )
    cmd.preprocess( 'flat', bias=offset_file )
    cmd.seqstat('pp_flat','pp_flat.csv', option='main')
    cmd.stack( 'pp_flat', type='rej', sigma_low=3.0, sigma_high=3.0, norm='mul', out='master_flat.fit')

# NOTE - Sigma low and High are set here for Darks
def master_dark(dark_dir, bias_file, seq_start, process_dir):
    cmd.cd(dark_dir)
    cmd.convertraw( 'dark', out=process_dir, start=seq_start )
    cmd.cd( process_dir )
    cmd.preprocess( 'dark', bias=bias_file )
    cmd.seqstat('pp_dark','pp_dark.csv', option='main')
    cmd.stack( 'pp_dark', type='rej', sigma_low=3.5, sigma_high=3.5, norm='no', out='master_dark.fit')

def pre_process_lights(camera, light_dir, bias_file, dark_file, seq_start, process_dir):
    cmd.cd(light_dir)
    if(camera=="ZWO_OSC"):
        cmd.convert( 'light', out=process_dir, start=seq_start )
    else:
        cmd.convertraw( 'light', out=process_dir, start=seq_start )
    cmd.cd( process_dir )
    cmd.seqstat('light','light.csv', option='main')

    if(camera=="ZWO_OSC"):
        # No Dark optimisation as cooled camera will expect to use Dark at same temperature, therefore no bias (Offset) specified here - it is part of pp_flats
        cmd.preprocess( 'light', flat='master_flat.fit', 
                        dark=dark_file, debayer=True, 
                        cfa=True, equalize_cfa=True, prefix='pp_')
    else:
        # Dark Optimised which requires the bias(Offset) , dark and Flat
        cmd.preprocess( 'light', bias=bias_file, flat='master_flat.fit', 
                        dark=dark_file, debayer=True, 
                        opt=True, cfa=True, equalize_cfa=True, prefix='pp_')
    cmd.seqstat('pp_light','pp_light.csv', option='main')

# Need to set a reference image as default will select the first, if this is rubbish (no or few stars)
# then fails.
# TO DO - when 2pass is provided then run as it is possible if the first image is poor then reference
# for the registration will be poor
def register_lights():    
    cmd.register( 'pp_light',prefix='r_' )
    cmd.seqstat('r_pp_light','r_pp_light.csv', option='main')

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
        sourceOffsetDir=os.path.join(arg_workingdir, 'DARKFLAT')
        sourceLightDir=os.path.join(arg_workingdir,'LIGHT', arg_targetname)
     
        indexStart=int(arg_sequencestart)
        print('*****************************************')
        print('Processing Started at ' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        print('*****************************************')
        print('  DIRECTORIES: -')
        print('    Working Directory = ' + arg_workingdir)
        print('    Processing for camera = ' + arg_camera)
        if arg_camera=="CANON_DSLR":
            global arg_masterbiasfile
            print('    Bias Master File = ' + arg_masterbiasfile)      
        if arg_camera=="ZWO_OSC":    
            global arg_masterdarkfile
            print('    Dark Master File = ' + arg_masterdarkfile)

        print('    Light Directory = ' + sourceLightDir)
        print('    Flat Directory = ' + sourceFlatDir)
        print('    Offset (DarkFlats/Bias) Directory = ' + sourceOffsetDir)
        print('    Dark Directory = ' + sourceDarkDir)
        print('    Process Directory = ' + processDir)
        print('\n  Options: -')
        print('    Index Start = ' + str(indexStart))
        print('    CPUs to use = ' + str(arg_cpus))
        print('    Process Stack = ' + arg_process)
        if arg_process=="stack":
            print('      Filter FWHM = ' + str(arg_filterfwhm))
            print('      Filter wFWHM = ' + str(arg_filterwfwhm))
            print('      Filter Roundness = ' + str(arg_filterround))
        print('*****************************************')

        # Prepare Master frames
        if arg_camera=="ZWO_OSC":
            fileCount = count_files(arg_camera, sourceOffsetDir)
            print ('Processing ' + str(fileCount) + ' offset')
            master_offset(arg_camera ,sourceOffsetDir, indexStart, processDir)
            arg_masterbiasfile = 'master_offset.fit'

        fileCount = count_files(arg_camera, sourceFlatDir)
        print ('Processing ' + str(fileCount) + ' flats')
        master_flat(arg_camera ,sourceFlatDir, arg_masterbiasfile, indexStart, processDir)
        
        if arg_camera=="CANON_DSLR":
            fileCount = count_files(arg_camera, sourceDarkDir)
            print ('Processing ' + str(fileCount) + ' darks')
            master_dark(sourceDarkDir, arg_masterbiasfile, indexStart, processDir)
            arg_masterdarkfile='master_dark.fit'
        
        # Dark optimisation and debayering is performed here
        fileCount = count_files(arg_camera, sourceLightDir)
        print ('Processing ' + str(fileCount) + ' lights')
        pre_process_lights(arg_camera, sourceLightDir, arg_masterbiasfile, arg_masterdarkfile, indexStart, processDir)

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
