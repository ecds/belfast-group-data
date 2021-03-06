
import glob
import networkx as nx
from networkx.readwrite import gexf
import rdflib
from rdflib.collection import Collection as RdfCollection

from belfastdata.rdfns import SCHEMA_ORG, DC

# first-pass attempt to generate weighted network based on
# type of rdf relation
connection_weights = {
    'sameAs': 10,
    'spouse': 9,
    'founder': 7,
    'founderOf': 7,
    'colleague': 4,
    'member': 5,
    'memberOf': 5,
    'knows': 2,
    'correspondedWith': 2,
    'publisher': 3,
    'association': 1,
    'affiliation': 1,
    'worksFor': 4,
    'mentions': 1,
    'alumniOf': 3,

    'about': 6,
    'creator': 7,
    'author': 7,
    'contributor': 6,
    'relatedLink': 4,
    'title': 3,
    'hasPart': 5,

    'birthPlace': 5,
    'workLocation': 4,
    'location': 4,
    'homeLocation': 4,

}



class Rdf2Gexf(object):

    # TODO: consider splitting out rdf -> nx logic from nx -> gexf

    def __init__(self, files, outfile):
        self.outfile = outfile

        self.graph = rdflib.Graph()
        for infile in files:
            self.graph.parse(infile)
        print '%d triples in %d files' % (len(self.graph), len(files))

        self.network = nx.MultiDiGraph()
        edge_labels = set()

        # iterate through rdf triples and add to the graph
        for triple in self.graph:
            subj, pred, obj = triple

            if pred == rdflib.RDF.first or pred == rdflib.RDF.rest:
                continue
            # FIXME: iterating through all triples results in
            # rdf sequences (first/rest) being handled weirdly...

            # make sure subject and object are added to the graph as nodes,
            # if appropriate
            self._add_nodes(triple)

            # get the short-hand name for property or edge label
            name = self._edge_label(pred)

            # if the object is a literal, add it to the node as a property of the subject
            if subj in self.network and isinstance(obj, rdflib.Literal) \
               or pred == rdflib.RDF.type:
                if pred == rdflib.RDF.type:
                    ns, val = rdflib.namespace.split_uri(obj)
                    # special case (for now)
                    if val == 'Manuscript':
                        if isinstance(self.graph.value(subj, DC.title), rdflib.BNode):
                            val = 'BelfastGroupSheet'

                else:
                    val = unicode(obj)
                self.network.node[subj][name] = val

            # otherwise, add an edge between the two resource nodes
            else:
                edge_labels.add(name)
                self.network.add_edge(subj, obj, label=name,
                                      weight=connection_weights.get(name, 1))

        print '%d nodes, %d edges' % (self.network.number_of_nodes(),
                                      self.network.number_of_edges())

        # TODO: useful for verbose output? (also report on relations with no weight?)
        #print 'edge labels: %s' % ', '.join(edge_labels)

        gexf.write_gexf(self.network, self.outfile)

    def _node_label(self, res):
        # NOTE: consider adding/calculating a preferredlabel
        # for important nodes in our data

        # use name first, if we have one
        name = self.graph.value(res, SCHEMA_ORG.name)
        if name:
            return name

        title = self.graph.value(res, DC.title)
        if title:
            # if title is a bnode, convert from list/collection
            if isinstance(title, rdflib.BNode):
                title_list = RdfCollection(self.graph, title)
                title = 'group sheet: ' + '; '.join(title_list)
                # truncate list if too long
                if len(title) > 50:
                    title = title[:50] + ' ...'

            # otherwise, title should be a literal (no conversion needed)

            return title

        # as a fall-back, use type for a label
        type = self.graph.value(res, rdflib.RDF.type)
        if type:
            ns, short_type = rdflib.namespace.split_uri(type)
            return short_type

    def _edge_label(self, pred):
        # get the short-hand name for property or edge label
        ns, name = rdflib.namespace.split_uri(pred)
        return name

    def _add_nodes(self, triple):
        subj, pred, obj = triple

        if self._include_as_node(subj) and subj not in self.network:
            self._add_node(subj)

        # special case: don't treat title list as a node in the network
        if pred == DC.title and isinstance(obj, rdflib.BNode):
            return

        if pred != rdflib.RDF.type and self._include_as_node(obj) \
           and obj not in self.network:
            self._add_node(obj)

    def _include_as_node(self, res):
        # determine if a URI should be included in the network graph
        # as a node
        if isinstance(res, rdflib.URIRef) or isinstance(res, rdflib.BNode):
            return True

    def _add_node(self, res):
        # add an rdf term to the network as a node
        attrs = {}
        label = self._node_label(res)
        if label is not None:
            attrs['label'] = label
        self.network.add_node(res, **attrs)

