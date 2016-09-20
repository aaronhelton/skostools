#!/usr/bin/env python
"""SKOS2XL

Additive/non-destructive conversion of SKOS Core style labels to very basic SKOS-XL style labels. Reads and writes any format supported by RDFLib.

Usage:
  skos2xl.py -i <infile> -o <outfile> -u <uri>

Options:
  -h --help               Show this screen
  -i --infile <infile>    SKOS Core compliant file to read from
  -o --outfile <outfile>  File to write to
  -u --uri <uri>          Base URI for instances
"""
from docopt import docopt
from rdflib import Graph, Namespace, Literal, URIRef, RDF
from rdflib.resource import Resource
from rdflib.namespace import SKOS, NamespaceManager
from rdflib.util import guess_format
import hashlib

if __name__ == '__main__':
  arguments = docopt(__doc__,version='SKOS2XL 1.0')
  infile = arguments['--infile']
  outfile = arguments['--outfile']
  uri = arguments['--uri']
  
  g = Graph()

  xl = Namespace('http://www.w3.org/2008/05/skos-xl#')
  base = Namespace(uri)
  
  nsm = NamespaceManager(g)
  # do we make the assumption that no SKOS-XL is already bound?
  nsm.bind('xl', xl, override=False)

  file_format = guess_format(infile)
  
  g.parse(infile,format=file_format)

  for s,o in g.subject_objects(predicate=SKOS.prefLabel):
    concept = Resource(g, s)
    hsh = hashlib.md5(o.encode('utf-8')).hexdigest()
    label = Resource(g, base.term('label/' + o.language + '_' + hsh))
    label.add(RDF.type, xl.Label)
    label.add(xl.literalForm, o)
    concept.add(xl.prefLabel, label)

  g.serialize(outfile, format=file_format)
