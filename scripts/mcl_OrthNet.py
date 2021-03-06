#!/usr/bin/env python

import sys, os, subprocess
import argparse
from argparse import RawTextHelpFormatter


###################################################
### 0. script description and parsing arguments ###
###################################################

synopsis1 = "\
 - runs mcl on OrthNets to remove spurious edges most likely resulted from\n\
    homology-synteny incongruence between 'BestHit' loci pairs.\n\
 - results can be piped into 'update_OrthNet_after_mcl.py', which tries to\n\
    update 'BestHitPairs' files to resolve the homology-synteny incogruence."
synopsis2 = "detailed description:\n\
 0. Pre-requisite: 'mcl' and 'parse_mclOutput.py' should be availalbe in $PATH\n\
 1. Input:\n\
  - expects './<Project>.clstrd.edges' generated by 'create_OrthNet.py' in the\n\
     Path2Input; a '*.clstrd.edges' file includes clusterID, query geneID (q), \n\
     subject geneID (s), CL_type(q->s), and CL_type(s->q), tab-delimited,\n\
     one edge per line and sorted by clusterIDs,\n\
  - '-i Path2Input': path to input files; default='.\'\n\
  - '-s'|'--single_copies': assumes the input file generated by\n\
     'create_OrthNet.py -s'; skip clusters containing only single-copy nodes.\n\
 2. Clustering process and parameters:\n\
  - if both CL_type(q->s) and CL_type(s->q) exist, the edge is reciprocal (rc).\n\
  - '-w weightMatrix': a tab-delimited text file including edge weights;\n\
     see the example file 'weights4mcl_OrthNet.list'; default values are:\n\
       TD	1.5 # weight for TD edges\n\
       CL_rc	1.2 # weight for rc CL edges\n\
       nCL_rc	0.5 # weight for rc non-CL edges\n\
       CL	0.6 # weight for non-rc (uni-directional) CL edges\n\
       nCL	0.25 # weight for non-rc (uni-directional) non-CL edges\n\
  - other parameters for mcl:\n\
     '-I graininess': 'graininess' of mcl; a value between 1.2 (rougher\n\
      clusters) and 5 (finer clusters); default=1.5\n\
     '-o Path2Output': path to temp and output files (dafault='./mcl').\n\
  - for each clstrID, create a temp input for mcl ('<Project>.clstrID.mclInput')\n\
     with quryID, sbjtID, and the edge weight, tab-delimited; runs mcl with the\n\
     'graininess' defined by '-I'; results are parsed by 'parse_mclOutput.py'.\n\
  - subclusters derived from cluster N by mcl are named N_0001, N_0002 ..., etc.\n\
 3. Output:\n\
  - parsed mcl results are combined and written to, if default parameters used:\n\
     '<Project>_TD1.5_rC1.2_rNC0.5_uC0.6_uNC0.25_I1.5_mclOutPC.txt', \n\
     (PC == Parsed and Concatanated); output filename can be modified with '-O'\n\
  - '-c'|'--clean_temp': remove all temp files.\n\
  - '-O output_ext': output file extension; default = "".txt""\n\n\
 by ohdongha@gmail.com ver0.2.2 20181023\n"

#version_history
#20181023 ver 0.2.2 # slight modification to make it working with parse_mclOutput.py ver1.0.5+ 
#20180516 ver 0.2.1 # accept path to input files as '-i'; added '-O' option for output file extension 
#20160918 ver 0.2 # accept weights as an input file with '-w' option
#20160829 ver 0.1 # added option to accept weights for TD edges 
#20160814 ver 0.0

parser = argparse.ArgumentParser(description = synopsis1, epilog = synopsis2, formatter_class = RawTextHelpFormatter)
 
## positional arguments
parser.add_argument('Project', type=str, help="See below")

## option to receive PATH to input and output files
parser.add_argument('-i', dest="Path2Input", default='./', help="see below")
parser.add_argument('-w', dest="weightMatrix", default="weights4mcl_OrthNet.list", help="see below")
parser.add_argument('-o', dest="Path2Output", type=str, default="./mcl", help="PATH for temp. and output files")
parser.add_argument('-c', '--clean_temp', action="store_true", default=False, help="clean temp. files after mcl runs")
parser.add_argument('-O', dest="output_ext", type=str, default=".txt", help="see below")

## option and parameters for mcl
parser.add_argument('-s', '--single_copies', action="store_true", default=False, help="see below")
#parser.add_argument('-Wd', '--WeightTD', dest="WeightTD", type=float, default=1, help="weight for tandem duplicated (TD) edges; see below") 
#parser.add_argument('-Wr', '--WeightRc', dest="WeightRc", type=float, default=1, help="weight for reciprocal (rc) edges; see below") 
#parser.add_argument('-Wn', '--WeightNRc', dest="WeightNRc", type=float, default=0.25, help="weight for non-rc edges; see below") 
parser.add_argument('-I', dest="graininess", type=float, default=1.5, help="'graininess' of mcl; see below")

args = parser.parse_args()

## setup PATHs and create Output directory, if not already exisiting
path_input = args.Path2Input
path_output = args.Path2Output
output_ext = args.output_ext
if path_input[-1] != "/": path_input = path_input + "/"
if path_output[-1] != "/": path_output = path_output + "/"
if output_ext[0] != ".": output_ext = '.' + output_ext

try: 
	os.makedirs(path_output)
except OSError:
	if not os.path.isdir(path_output): raise

	
##################################
### 1. reading in edge weights ###
##################################
fin_weights4edges = open(args.weightMatrix, "rU")
edgeWeights_dict = dict() # dict with key = edge_type, value = weight

for line in fin_weights4edges:
	tok = line.split('\t')
	if len(tok) >= 2:
		edgeWeights_dict[tok[0].strip()] = float(tok[1].strip())

if 'TD' not in edgeWeights_dict:
	edgeWeights_dict['TD'] = 1.5
	print "weight for TD edges not given, using default value of TD = 1.5"
if 'CL_rc' not in edgeWeights_dict:
	edgeWeights_dict['CL_rc'] = 1.2
	print "weight for reciprocal CL edges not given, using default value of CL_rc = 1.2"
if 'nCL_rc' not in edgeWeights_dict:
	edgeWeights_dict['nCL_rc'] = 0.5
	print "weight for reciprocal non-CL edges not given, using default value of nCL_rc = 0.5"
if 'CL' not in edgeWeights_dict:
	edgeWeights_dict['CL'] = 0.6
	print "weight for unidirectional CL edges not given, using default value of CL = 0.6"
if 'nCL' not in edgeWeights_dict:
	edgeWeights_dict['nCL'] = 0.25
	print "weight for unidirectional non-CL edges not given, using default value of nCL = 0.25"
print "done reading the edge weight matrix file %s" % fin_weights4edges.name
fin_weights4edges.close()
	
#####################################################################
### 2. reading <Project>.clstrd.edges and creating mclInput files ###
#####################################################################

fin_edges = open(path_input + args.Project + '.clstrd.edges', "rU")
Header = True

clstrID_prev = ""
clstrID = ""
node1ID = ""
node2ID = ""
CLtype_12 = ""
CLtype_21 = ""
clstrs_4mcl_list = []
num_clstrs_all = 0
process_clstr = False

for line in fin_edges:
	if Header == True:
		Header = False
	else:
		tok = line.split('\t')
		clstrID_prev = clstrID
		clstrID = tok[0].strip()
		node1ID = tok[1].strip()
		node2ID = tok[2].strip()
		CLtype_12 = tok[3].strip()
		CLtype_21 = tok[4].strip()
		# open a file for new cluster:
		if clstrID != clstrID_prev:
			num_clstrs_all = num_clstrs_all + 1
			if args.single_copies == False or ( args.single_copies == True and tok[5].strip() != '1' ):
				try:
					fout_mclInput_clstr.close() # close the previous mclInput file
				except NameError:
					pass
				fout_mclInput_clstr = open( path_output + args.Project + '.' + clstrID + '.mclInput', 'w') # open a new mclInput file
				clstrs_4mcl_list.append(clstrID)
				process_clstr = True
			else:
				process_clstr = False
		if process_clstr == True:
			if CLtype_12 == 'TD' and CLtype_21 == 'TD':
				fout_mclInput_clstr.write(node1ID + '\t' + node2ID + '\t' + str(edgeWeights_dict['TD']) + '\n')
			elif CLtype_12.split('_')[0] == 'cl' and CLtype_21.split('_')[0] == 'cl':
				fout_mclInput_clstr.write(node1ID + '\t' + node2ID + '\t' + str(edgeWeights_dict['CL_rc']) + '\n')
			elif CLtype_12 != '-' and CLtype_21 != '-':
				fout_mclInput_clstr.write(node1ID + '\t' + node2ID + '\t' + str(edgeWeights_dict['nCL_rc']) + '\n')
			elif CLtype_12.split('_')[0] == 'cl' or CLtype_21.split('_')[0] == 'cl':
				fout_mclInput_clstr.write(node1ID + '\t' + node2ID + '\t' + str(edgeWeights_dict['CL']) + '\n')
			else:
				fout_mclInput_clstr.write(node1ID + '\t' + node2ID + '\t' + str(edgeWeights_dict['nCL']) + '\n')
				
fout_mclInput_clstr.close() # close the last mclInput file
print "%d mclInput files were created, out of %d total clusters" % (len(clstrs_4mcl_list), num_clstrs_all)


###################
### 3. runs mcl ###
###################

fileName_mclInput = ""
fileName_mclOutput = ""
fileName_mclOutput_parsed = ""
fileName_mclOutput_parsed_combined = path_output + args.Project \
			+ '_TD' + str(edgeWeights_dict['TD']) \
			+ '_rC' + str(edgeWeights_dict['CL_rc']) \
			+ '_rNC' + str(edgeWeights_dict['nCL_rc']) \
			+ '_uC' + str(edgeWeights_dict['CL']) \
			+ '_uNC' + str(edgeWeights_dict['nCL']) \
			+ '_I' + str(args.graininess) + "_mclOutPC" + output_ext
num_lines = 0
num_clstrs_modified = 0
num_subclstrs_all = 0

beginning = True
for clstrID in clstrs_4mcl_list:
	fileName_mclInput = path_output + args.Project + '.' + clstrID + '.mclInput'
	fileName_mclOutput = path_output + args.Project + '.' + clstrID + '.mclOutput'
	fileName_mclOutput_parsed = path_output + args.Project + '.' + clstrID + '.mclOutput.parsed.txt'	
#	subprocess.call("mcl " + fileName_mclInput + " -q x -V all --abc -I " + str(args.graininess) \
#			+ " -o " + fileName_mclOutput, shell=True) # hard to make mcl complitely quiet
	subprocess.call("mcl " + fileName_mclInput + " --abc -V all -I " + str(args.graininess) \
			+ " -o " + fileName_mclOutput, shell=True)
	num_lines = 0
	for line in open(fileName_mclOutput):
		num_lines = num_lines + 1
	if num_lines > 1:
#		subprocess.call("parse_mclOutput.py " + fileName_mclOutput + " " + clstrID, shell=True)
		subprocess.call("parse_mclOutput.py " + fileName_mclOutput + " " + clstrID + " -o " + fileName_mclOutput, shell=True) # ver 0.2.2
		if beginning:
			subprocess.call("cat " + fileName_mclOutput_parsed + " > " + fileName_mclOutput_parsed_combined, shell=True)
			beginning = False
		else:
			subprocess.call("cat " + fileName_mclOutput_parsed + " >> " + fileName_mclOutput_parsed_combined, shell=True)
		num_clstrs_modified = num_clstrs_modified + 1
		num_subclstrs_all = num_subclstrs_all + num_lines

print "out of %d total clusters, %d were subjected to mcl, which further divided %d clusters into %d sub-clusters." \
			% (num_clstrs_all, len(clstrs_4mcl_list), num_clstrs_modified, num_subclstrs_all)
			
###################
### 4. cleaning ###
###################
if args.clean_temp:
	print "cleaning temporary files"
	subprocess.call("rm " + path_output + args.Project + ".*.mclInput", shell=True)
	subprocess.call("rm " + path_output + args.Project + ".*.mclOutput", shell=True)
	subprocess.call("rm " + path_output + args.Project + ".*.mclOutput.parsed.txt", shell=True)	
print("done")