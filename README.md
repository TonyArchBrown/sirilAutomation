# sirilAutomation
Automated processing of Astronomy images using Siril

## Command Line Execution
Simply run the PreProcess.py file with parameters:-

python3 PreProcess.py -b <Master bias file path> -t <Target location name> -p <stage> -f <filter FWHM> -w <filter wFWHM> -r <filter Roundness> -d <base directory> -s <Start Index>

The assumption when running the command is that there will be a directory layout as follows: -
Base Directory
|-Darks
  |-*.cr2
|-Flats
  |-*.cr2
|-Lights
  |-Target
    |--*.cr2
    
### Base Directory -d
Optional - if no base directory is provided then the current working directory is assumed to be the directory otherwise provide the path to the base directory

### Master bias file path -b
Required - path and name of the master bias file to use to use for the pre-processing of files

### Target location name -t
Required - Source light files are expecting to be in a folder that corresponds to the target.  

### Stage -p
Optional - if not provided then full Preprocessing / registration and stacking will be performed,  otherwise tell the script to stop at a stage of your choosing.  This allows manual intervention for example to run a background extraction on each pre processed light, or to manually filter out post registration.
* preproc - create master flats and darks using the master bias, then preprocess the lights using optimised darks option
* reg - perform the registration on all the pre-processed frames.  
* stack - perform the stacking of registered files.  Filters can be provided, otherwise all frames will be used.  See the Filters section.

### Start Index -s
Not currently working due to Siril bug (1.0.5).  Intention is to allow a starting number ot be used as the sequence number for all images, this would allow multi night session to be allocated a block of numbers and therefore make the subsequent registration and stacking of all session files easier as filenames would not overlap.

### Filters 
When performing Stage = stack then the following filters can be defined to remove frames outside of these values.

#### filter FWHM -f
Do not stack frames where the light frame's FWHW values is greater than this value.  Useful number to start with is 3.5, some will think this not strict enough!

#### filter wFWHM -w
Do not stack frames where the light frame's weighted FWHW values is greater than this value.  Useful number to start with is 5, some will think this not strict enough!

#### filter Roundness -r
Do not stack frames where the light frame's Roundness is less than this value.  Useful number to start with is 0.8, 80% roundness is practically indistinguishable from round.
