import sys
import argparse
import xls2py as x2p
import re
from datetime import date
import logging

import init_utils as iu
import import_utils as util
from db.models import Antibody, Protein
from django.db import transaction

__version__ = "$Revision: 24d02504e664 $"
# $Source$

# ---------------------------------------------------------------------------

import setparams as _sg
_params = dict(
    VERBOSE = False,
    APPNAME = 'db',
)
_sg.setparams(_params)
del _sg, _params

# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

@transaction.commit_on_success
def main(path):
    """
    Read in the Antibody
    """
    sheet_name = 'Sheet1'
    sheet = iu.readtable([path, sheet_name, 1]) # Note, skipping the header row by default

    properties = ('model_field','required','default','converter')
    column_definitions = { 
              'facility_id': ('facility_id',True),
              'name': ('name',True),
              'alternative_names': 'alternative_names',
              'clone_name': 'clone_name',
              'antibody_registry_id': 'antibody_registry_id',
              'lincs_id': 'lincs_id',
              'target_protein_lincs_id':'target_protein',
              'non_protein_target_name': 'non_protein_target_name',
              'target_organism': 'target_organism',
              'antibody_type': 'antibody_type',
              'immunogen': 'immunogen',
              'immunogen_sequence': 'immunogen_sequence',
              'source_organism': 'source_organism',
              'species': 'species',
              'clonality': 'clonality',
              'isotype': 'isotype',
              'production_details': 'production_details',
              'labeling': 'labeling',
              'labeling_details': 'labeling_details',
              'relevant_references': 'relevant_references',
              'Date Data Received':('date_data_received',False,None,util.date_converter),
              'Date Loaded': ('date_loaded',False,None,util.date_converter),
              'Date Publicly Available': ('date_publicly_available',False,None,util.date_converter),
              'Most Recent Update': ('date_updated',False,None,util.date_converter),
              'Is Restricted':('is_restricted',False,False)}

              
    # convert the labels to fleshed out dict's, with strategies for optional, default and converter
    column_definitions = util.fill_in_column_definitions(properties,column_definitions)
    
    # create a dict mapping the column ordinal to the proper column definition dict
    cols = util.find_columns(column_definitions, sheet.labels)

    rows = 0    
    logger.debug(str(('cols: ' , cols)))
    for row in sheet:
        r = util.make_row(row)
        dict = {}
        initializer = {}
        for i,value in enumerate(r):
            if i not in cols: continue
            properties = cols[i]

            logger.debug(str(('read col: ', i, ', ', properties)))
            required = properties['required']
            default = properties['default']
            converter = properties['converter']
            model_field = properties['model_field']

            # Todo, refactor to a method
            logger.debug(str(('raw value', value)))
            if(converter != None):
                value = converter(value)
            if(value == None ):
                if( default != None ):
                    value = default
            if(value == None and  required == True):
                raise Exception(
                    'Field is required: %s, record: %d' % (properties['column_label'],rows))
            logger.debug(str(('model_field: ' , model_field, ', value: ', value)))
            initializer[model_field] = value
            
        try:
            logger.debug(str(('initializer: ', initializer)))
            if initializer['target_protein']:
                initializer['target_protein'] = \
                    Protein.objects.get(lincs_id=initializer['target_protein'])
        except Exception, e:
            logger.error(str(( 
                "Protein table entry for Target protein HMS LINCS ID not found: ", 
                initializer['target_protein'], initializer)))
            raise
            
        try:
            logger.debug(str(('initializer: ', initializer)))
            antibody = Antibody(**initializer)
            antibody.save()
            logger.info(str(('antibody created: ', antibody)))
            rows += 1
        except Exception, e:
            logger.error(str(( "Invalid antibody initializer: ", initializer)))
            raise
        
    print "Rows read: ", rows
    
    

parser = argparse.ArgumentParser(description='Import file')
parser.add_argument('-f', action='store', dest='inputFile',
                    metavar='FILE', required=True,
                    help='input file path')
parser.add_argument('-v', '--verbose', dest='verbose', action='count',
                help="Increase verbosity (specify multiple times for more)")    

if __name__ == "__main__":
    args = parser.parse_args()
    if(args.inputFile is None):
        parser.print_help();
        parser.exit(0, "\nMust define the FILE param.\n")

    log_level = logging.WARNING # default
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG
    # NOTE this doesn't work because the config is being set by the included settings.py, and you can only set the config once
    logging.basicConfig(level=log_level, format='%(msecs)d:%(module)s:%(lineno)d:%(levelname)s: %(message)s')        
    logger.setLevel(log_level)

    print 'importing ', args.inputFile
    main(args.inputFile)
