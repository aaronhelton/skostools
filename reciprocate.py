#!/usr/bin/env python
"""reciprocate

Detect and fix non-reciprocated assertions in RDF files. This is a basic integrity constraint tool, but it isn't a validator. Use with the understanding that the resulting reciprocations may or may not be valid or even wanted. The namespace prefixes for the predicate and reciprocals must match.

Usage:
  reciprocate.py -i <infile> -o <outfile> -p <predicate> -r <reciprocal>

Example:
  reciprocate.py -i bad.ttl -o good.ttl -p skos:inScheme -r skos:hasTopConcept

  This searches the graph for (s,p,o) patterns matching (s,skos:inScheme,o) and adding reciprocal assertion (o,skos:hasTopConcept,s).

Options:
  -h --help                     Show this screen
  -i --infile <infile>          RDF file to read from
  -o --outfile <outfile>        RDF file to write to
  -p --predicate <predicate>    Namespaced predicate that lacks reciprocation
  -r --reciprocal <reciprocal>  Namespaced predicate that is the reciprocal of --predicate
"""
from docopt import docopt
from rdflib import Graph, Namespace, Literal, URIRef, RDF
from rdflib.resource import Resource
from rdflib.namespace import SKOS, NamespaceManager
from rdflib.util import guess_format
import sys,hashlib

if __name__ == '__main__':
  arguments = docopt(__doc__,version='reciprocate 1.0')
  infile = arguments['--infile']
  outfile = arguments['--outfile']
  predicate = arguments['--predicate']
  reciprocal = arguments['--reciprocal']

  g = Graph()
  g.parse(infile,format=guess_format(infile))

  nsm = NamespaceManager(g)

  # r_namespace should == p_namespace, otherwise how can they really be reciprocals?
  (p_namespace,p_verb) = predicate.split(":")
  (r_namespace,r_verb) = reciprocal.split(":")

  assert p_namespace == r_namespace, "Prefixes don't match. This would probably create weird reciprocations."

  # find out if the namespaces are already registered via the graph, because they *should* be

  # I wonder if there's a more efficient way of doing this. Namespaces aren't usually prohibitively numerous, but still.
  nuri = ''
  for (p,n) in g.namespaces():
    if p == p_namespace:
      nuri = Namespace(n)
      nsm.bind(p,nuri,override=False)

  if nuri == '':
    # we lack a proper prefix/namespace definition and can't continue
    sys.exit("\nError: Can't find the prefix in the namespace list for this graph. Are you sure it's there?\n")

  found_p = getattr(nuri,p_verb)
  found_r = getattr(nuri,r_verb)

  for (s,o) in g.subject_objects(predicate = found_p):
    new_subject = Resource(g, o)
    new_object = Resource(g, s)
    new_subject.add(found_r,new_object)

  g.serialize(outfile,guess_format(infile))
