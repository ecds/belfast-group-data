#!/usr/bin/env python

import glob
import json
import networkx as nx
from networkx.readwrite import gexf
import rdflib

# simple script to load rdf data and convert into a networkx graph,
# then exported as GEXF for manual interaction with tools like Gephi


SCHEMA_ORG = rdflib.Namespace('http://schema.org/')
DC = rdflib.Namespace('http://purl.org/dc/terms/')


def get_best_label(res, graph):
    # NOTE: we should consider adding/calculating a preferredlabel
    # for important nodes in our data
    title = graph.value(res, DC.title)
    if title:
        return title
    name = graph.value(res, SCHEMA_ORG.name)
    if name:
        return name

    # as a fall-back, use type for a label
    type = graph.value(res, rdflib.RDF.type)
    if type:
        ns, short_type = rdflib.namespace.split_uri(type)
        return short_type

# load all the data into a single rdf graph
g = rdflib.Graph()
files = 0
for infile in glob.iglob('data/*.xml'):
    g.parse(infile)
    files +=1

print '%d triples in %d files' % (len(g), files)

nxg = nx.Graph()

# iterate through rdf triples and add to the graph
for subj, pred, obj in g:
    # make sure subject and object (if a resource) are added to the graph as nodes
    if isinstance(subj, rdflib.URIRef) or isinstance(subj, rdflib.BNode) \
          and subj not in nxg:
        add_opts = {}
        label = get_best_label(subj, g)
        if label is not None:
            add_opts['label'] = label
            nxg.add_node(subj, **add_opts)


    if pred is not rdflib.RDF.type and \
            (isinstance(obj, rdflib.URIRef) or isinstance(obj, rdflib.BNode)) \
            and obj not in nxg:
        add_opts = {}
        label = get_best_label(obj, g)
        if label is not None:
           add_opts['label'] = label
        nxg.add_node(obj, **add_opts)

    # get the short-hand name for property or edge label
    ns, name = rdflib.namespace.split_uri(pred)

    # if the object is a literal, add it to the node as a property of the subject
    if isinstance(obj, rdflib.Literal) or pred == rdflib.RDF.type:
        if pred == rdflib.RDF.type:
            ns, val = rdflib.namespace.split_uri(obj)
        else:
            val = unicode(obj)
        nxg.node[subj][name] = val

    # otherwise, add an edge between the two resource nodes
    else:
        nxg.add_edge(subj, obj, label=name)


print '%d nodes, %d edges' % (nxg.number_of_nodes(), nxg.number_of_edges())

gexf.write_gexf(nxg, 'belfast-group-data.gexf')
