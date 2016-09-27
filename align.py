#!/usr/bin/env python
"""align.py

Simple non-interactive label-based alignment tool for SKOS Core formatted Concept Schemes. Input can be in any RDFLib supported format. Output is whatever format the lefthand file had. While it is possible for this script to consume SKOS-XL, it requires the presence of SKOS Core style labels. It simply ignores SKOS-XL.

Usage:
  align.py -f <left> -r <right> -o <outfile>

Options:
  -h --help               Show this screen
  -f --left <left>        Lefthand file to load
  -r --right <right>      Righthand file to load
  -o --outfile <outfile>  File to write to
"""
from docopt import docopt
from rdflib import Graph, Namespace, Literal, URIRef, RDF, OWL
from rdflib.resource import Resource
from rdflib.namespace import SKOS, NamespaceManager
from rdflib.util import guess_format
import hashlib
import logging

if __name__ == '__main__':
  arguments = docopt(__doc__,version='SKOS2XL 1.0')
  leftfile = arguments['--left']
  rightfile = arguments['--right']
  outfile = arguments['--outfile']

  logging.basicConfig(filename='align.log',level=logging.DEBUG)

  left_graph = Graph()
  right_graph = Graph()
  left_format = guess_format(leftfile)
  print("Loading " + leftfile)
  left_graph.parse(leftfile, format=left_format)
  print("Loading " + rightfile)
  right_graph.parse(rightfile, format=guess_format(rightfile))

  # let's make dictionaries with keys set to label values and values set to corresponding URI
  # then we can do a couple of basic transformations and try key lookups, which should be 
  # faster than string searches

  left_labels = {}
  right_labels = {}
  owl_sameas = {}
  match_ids = []
  unmatched = []
  unmatched_deletions = []

  # set the minimum score, which is the integer count of matching labels
  min_score = 2

  print("Making dictionaries")
  for s,o in left_graph.subject_objects(predicate=SKOS.prefLabel):
    if o.value.isupper():
      label_key = o.value + '_' + o.language.upper()
    elif o.value.islower():
      label_key = o.value + '_' + o.language.lower()
    else:
      label_key = o.value + '_' + o.language

    logging.debug("Adding " + label_key + " to left_labels with URI " + str(s))
    left_labels[label_key] = str(s)

  for s,o in right_graph.subject_objects(predicate=SKOS.prefLabel):
    if o.value.isupper():
      label_key = o.value + '_' + o.language.upper()
    elif o.value.islower():
      label_key = o.value + '_' + o.language.lower()
    else:
      label_key = o.value + '_' + o.language

    logging.debug("Adding " + label_key + " to right_labels with URI " + str(s))
    right_labels[label_key] = str(s)

  print("Searching labels")
  for key in left_labels:
    right_match = None
    # straight comparison
    logging.debug("Does right_labels have " + key + "?")
    try:
      right_match = right_labels[key]
    except KeyError:
      logging.debug("No. What about " + key.upper() + "?")
      #upcase left
      try:
        right_match = right_labels[key.upper()]
      except KeyError:
        logging.debug("No. What about " + key.lower() + "?")
        #downcase left
        try:
          right_match = right_labels[key.lower()]
        except KeyError:
          logging.debug("Can't find " + key + " in right_labels under any circumstance. Passing.")
          # stop here; nothing seems to match, so likely there is no match from left to right?
          pass
 

    if right_match:
      # make a match hash combining right and left URIs to use as an identifier. We can iterate a 
      # score to weed out near matches so we can promote those that match across all translations
      match_id = hashlib.md5(right_match.encode('utf-8') + left_labels[key].encode('utf-8')).hexdigest()
      match_ids.append(match_id)
      logging.debug(match_id)
      try:
        osa = owl_sameas[match_id]
      except KeyError:
        owl_sameas[match_id] = {
          'left':left_labels[key],
          'right':right_match,
          'score':0
        }
      finally:
        owl_sameas[match_id]['score'] += 1
        # because something eventually matched here, we can mark the item as to be deleted from unmatched
        if left_labels[key] not in unmatched_deletions:
          unmatched_deletions.append(left_labels[key])
        logging.debug(owl_sameas[match_id])
    else:
      # we want a way to catalog things that end up without any kind of match. Let's start here.
      if left_labels[key] not in unmatched:
        unmatched.append(left_labels[key])


  out_graph = Graph()
  nsm = NamespaceManager(out_graph)
  nsm.bind('owl', OWL, override=False)
  
  print("Count of matches: " + str(len(match_ids)))

  for i in match_ids:
    osa = owl_sameas[i]
    if osa['score'] >= min_score:
      f = Resource(out_graph, URIRef(osa['left']))
      r = Resource(out_graph, URIRef(osa['right']))
      f.add(OWL.sameAs, r)
      r.add(OWL.sameAs, f)
    else:
      # The match was excluded by score
      print("Excluding " + str(osa) + " because the score was too low.")

  out_graph.serialize(outfile,format=left_format)
  if len(unmatched) > 0:
    if len(unmatched_deletions) > 0:
      unmatched = list(set(unmatched) - set(unmatched_deletions)) 
    for u in unmatched:
      print(u + " matched nothing in the target set.")
