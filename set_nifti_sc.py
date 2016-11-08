#!/usr/bin/python

import sys
import os
from subprocess import Popen, PIPE
import optparse
import tempfile
import shutil


def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


def which(program):
    assert isinstance(program, str)
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


class FslToolExecuteException(Exception):
    pass


class NiftiConvention(object):
    def __init__(self):
        self.tmp_folder = ''
        self.fslorient_bin = ''
        self.fslswapdim_bin = ''
        self.options = None
        self.neuro_default = 'LR AP SI'
        self.radio_default = 'RL AP SI'
        self.valid_chars = [['L', 'R'], ['A', 'P'], ['S', 'I']]
        self.fslbinary_names = [['fsl5.0-fslorient', 'fsl5.0-fslswapdim'],
                                ['fslorient', 'fslswapdim']]

    def convention_is_valid(self, convention_string):
        c_in_indicator = [False, False, False]
        is_valid = True
        if not len(convention_string) is 4:
            is_valid = False

        if not convention_string[0] in ['R', 'N']:
            is_valid = False

        for letter in convention_string[1:]:
            for i in range(len(self.valid_chars)):
                if letter in self.valid_chars[i] and c_in_indicator[i] is True:
                    is_valid = False
                elif letter in self.valid_chars[i]:
                    c_in_indicator[i] = True

        if not all(c_in_indicator):
            is_valid = False

        return is_valid

    def short_to_long_convention(self, short_conv):

        long_conv = ''
        assert len(short_conv) is 3
        for letter in short_conv:
            for vc in self.valid_chars:
                if letter in vc:
                    long_conv += letter
                    long_conv += vc[vc.index(letter) - 1] + ' '

        long_conv = long_conv[0:-1]
        return long_conv

    @property
    def check_fslbinaries(self):
        """
        checks for existence of fls binaries in the system path
        :return: true if binaries are found and false if not found
        """
        binaries_found = False
        for b_names in self.fslbinary_names:
            if which(b_names[0]) and which(b_names[1]):
                binaries_found = True
                self.fslorient_bin = b_names[0]
                self.fslswapdim_bin = b_names[1]

        return binaries_found

    def is_radiological_conv(self, filepath):
        command = self.fslorient_bin + ' -getorient ' + filepath
        output = self.execute(command)

        if output[0].strip('\n') == 'RADIOLOGICAL':
            input_is_r = True
        elif output[0].strip('\n') == 'NEUROLOGICAL':
            input_is_r = False
        else:
            raise Exception('Radiological nor Neurological status could be determined')

        return input_is_r

    def swap_orient(self, filepath, is_radiologcal):

        # left right needs to be first dimension
        if is_radiologcal:
            self.swap_dim(filepath, self.radio_default)
        else:
            self.swap_dim(filepath, self.neuro_default)

        command = self.fslorient_bin + ' -swaporient ' + filepath
        self.execute(command)
        self.swap_dim(filepath, '-x y z')

    def execute(self, command):

        if self.options.verbose:
            print 'Command: ' + command
        stream = Popen(command, stdout=PIPE, shell=True)
        rcode = stream.wait()
        output = stream.communicate()

        if rcode:
            err = FslToolExecuteException(command, output)
            err.message = "FSL tool execution failed"
            raise err
        if self.options.verbose:
            print output

        return output

    def swap_dim(self, filepath, convention):

        command = self.fslswapdim_bin + ' ' + filepath + ' ' + convention + ' ' + filepath
        self.execute(command)

    def run(self):

        input_file = ''
        output_file = ''

        # check for fls binaries
        binaries_found = self.check_fslbinaries
        if not binaries_found:
            sys.exit("Error: FSL binaries not found, make sure binaries are added to the system path")

        usage = "usage: nifti_convention <inputfile> <outputfile>  [options]"
        parser = optparse.OptionParser(usage=usage,
                                       description="Changing the convention how the data ist stored in the nifti file."
                                                   "The anatomical labels (orientation) need "
                                                   "to be set correctly for the tool to yield the desired result."
                                                   " FSL tools (http://fsl.fmrib.ox.ac.uk/) is "
                                                   "required to be installed. The tool performs a series of "
                                                   "-fslorient and -fslswapdim commands to change the "
                                                   "storage convention.")
        parser.add_option('-c', help="nifti storage convention [default: RRAS] "
                                     "4 letters [R,N] [L,R] [A,P] [S,I] defining how data is stored in the nifti file. "
                                     "first letter: [R,N] for radiological or neurological convention. "
                                     "letter 2-4: convention for the dimensions R=RightLeft, A=AnteriorPosterior,"
                                     " S=SuperiorInferior",
                          action='store', type='string', dest='convention', default='RRAS')
        parser.add_option('-v', help="verbose", action='store_true', dest='verbose', default=False)

        self.options, args = parser.parse_args()
        self.options.convention = self.options.convention.upper()

        if not args:
            parser.error('No input file given')
        elif not os.path.isfile(args[0]):
            parser.error('Input file does not exist!')
        else:
            input_file = args[0]
        if len(args) < 2:
            parser.error('No output file given')
        else:
            output_file = args[1]
        if len(args) < 2:
            print "Warning: Additional argument ignored!"
        if not self.convention_is_valid(self.options.convention):
            parser.error(
                "Convention argument is not valid! Only a combination of these 4 letters "
                "[R,N] [L,R] [A,P] [I,S] is allowed!")

        if self.options.verbose:
            print "Input file: " + input_file
            print "Output file: " + output_file

        if not output_file.endswith('.nii.gz'):
            print "Warning: Output file will be zipped to a .nii.gz file"
            if not output_file.endswith('.nii'):
                output_file += '.nii.gz'
            else:
                output_file += '.gz'

        if not (input_file.endswith('.nii') or input_file.endswith('.nii.gz')):
            print parser.error('Input file must be a nifti file!')

        # special case, fsl tools does not work with multiple dots in filenmae
        file_extension = '.nii.gz'

        self.tmp_folder = tempfile.mkdtemp()

        # copy input to tmp folder
        working_input = os.path.join(self.tmp_folder, 'input' + file_extension)
        if self.options.verbose:
            print "Working input: " + working_input
        shutil.copy(input_file, working_input)

        # check for convention
        is_radiological = self.is_radiological_conv(working_input)

        # change orientation if we have to
        if (self.options.convention[0] is 'R' and not is_radiological) or (
                        self.options.convention[0] is 'N' and is_radiological):
            self.swap_orient(working_input, is_radiological)

        # swap the dimensions to the desired convention
        self.swap_dim(working_input, self.short_to_long_convention(self.options.convention[1:]))

        # copy file to destination
        shutil.copy(working_input, output_file)

    def __del__(self):
        if os.path.isdir(self.tmp_folder):
            shutil.rmtree(self.tmp_folder, ignore_errors=True)


if __name__ == "__main__":
    try:
        nc = NiftiConvention()
        nc.run()
        exit(0)
    except FslToolExecuteException, e:
        print 'Error: ' + e.message
        if e[1][0].startswith('Cannot perform requested swap'):
            print "The given convention is not allowed! Try to use the default convention."
        exit(1)
