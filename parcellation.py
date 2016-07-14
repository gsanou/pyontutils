#!/usr/bin/env python3

import os
import glob
from datetime import date
from collections import namedtuple
import requests
import rdflib
from rdflib.extras import infixowl
from lxml import etree
from utils import add_hierarchy, makeGraph, rowParse
from IPython import embed


PScheme = namedtuple('PScheme', ['curie', 'name', 'species', 'devstage', 'citation'])
PScheme('ilx:something','some parcellation scheme concept','NCBITaxon:1234','adult','Bob Jones said so')

PARC_SUPER = ('ilx:ilx_brain_parcellation_concept', 'Brain parcellation scheme concept')
TODAY = date.isoformat(date.today())

def make_scheme(scheme, parent=PARC_SUPER[0]):  # ick...
    out = [
        (scheme.curie, rdflib.RDF.type, rdflib.OWL.Class),
        (scheme.curie, rdflib.RDFS.label, scheme.name),
        (scheme.curie, rdflib.RDFS.subClassOf, parent),
        (scheme.curie, 'ilx:has_taxon', scheme.species),
        (scheme.curie, 'ilx:has_developmental_stage', scheme.devstage),
        (scheme.curie, 'OBOANN:definingCitation', scheme.citation),
    ]
    return out

def add_scheme(graph, scheme, parent=None):
    if not parent:
        [graph.add_node(*triple) for triple in make_scheme(scheme)]
    else:
        [graph.add_node(*triple) for triple in make_scheme(scheme, parent)]

def parcellation_schemes(ontids):
    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/'
    filename = 'parcellation'
    ontid = ONT_PATH + filename + '.ttl'
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
    }
    new_graph = makeGraph(filename, PREFIXES)
    new_graph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    new_graph.add_node(ontid, rdflib.RDFS.label, 'NIF collected parcellation schemes ontology')
    new_graph.add_node(ontid, rdflib.RDFS.comment, 'Brain parcellation schemes as represented by root concepts.')
    new_graph.add_node(ontid, rdflib.OWL.versionInfo, TODAY)

    for import_id in sorted(ontids):
        new_graph.add_node(ontid, rdflib.OWL.imports, import_id)
    new_graph.add_node(PARC_SUPER[0], rdflib.RDF.type, rdflib.OWL.Class)
    new_graph.add_node(PARC_SUPER[0], rdflib.RDFS.label, PARC_SUPER[1])
    new_graph.write(delay=True)

def mouse_brain_atlas():
    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/generated/'
    filename = 'mbaslim'
    ontid = ONT_PATH + filename + '.ttl'
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'obo':'http://purl.obolibrary.org/obo/',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        'MBA':'http://api.brain-map.org/api/v2/data/Structure/',
        'owl':'http://www.w3.org/2002/07/owl#',  # this should autoadd for prefixes but doesnt!?
    }
    new_graph = makeGraph(filename, PREFIXES)
    new_graph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    new_graph.add_node(ontid, rdflib.RDFS.label, 'Allen Mouse Brain Atlas Ontology')
    new_graph.add_node(ontid, rdflib.RDFS.comment, 'This file is automatically generated from the Allen Brain Atlas API')
    new_graph.add_node(ontid, rdflib.OWL.versionInfo, TODAY)
    meta = PScheme('ilx:allen_brain_parc_region',
                   'Allen Mouse Brain Atlas parcellation concept',
                   'NCBITaxon:10090',
                   'adult P56',
                   'http://help.brain-map.org/download/attachments/2818169/AllenReferenceAtlas_v2_2011.pdf?version=1&modificationDate=1319667383440')  # yay no doi! wat
    add_scheme(new_graph, meta)
    #superclass = rdflib.URIRef('http://uri.interlex.org/base/ilx_allen_brain_parc_region')
    #new_graph.add_node(superclass, rdflib.RDFS.label, 'Allen Mouse Brain Atlas brain region')
    #new_graph.add_node(superclass, rdflib.RDFS.subClassOf, PARC_SUPER[0])
    c_prefix, c_suffix = meta.curie.split(':')
    superclass = new_graph.namespaces[c_prefix][c_suffix]

    aba_map = {
        'acronym':new_graph.namespaces['OBOANN']['acronym'],  # FIXME all this is BAD WAY
        #'id':namespaces['ABA'],
        'name':rdflib.RDFS.label,
        #'parent_structure_id':rdflib.RDFS['subClassOf'],
        'safe_name':new_graph.namespaces['OBOANN']['synonym'],
    }

    def aba_trips(node_d):
        output = []
        parent = 'MBA:' + str(node_d['id'])  # FIXME HRM what happens if we want to change ABA:  OH LOOK
        for key, edge in sorted(aba_map.items()):
            value = node_d[key]
            if not value:
                continue
            elif key == 'safe_name' and value == node_d['name']:
                continue  # don't duplicate labels as synonyms
            output.append( (parent, edge, value) )
        return output

    root = 997  # for actual parts of the brain
    url = 'http://api.brain-map.org/api/v2/tree_search/Structure/997.json?descendants=true'
    resp = requests.get(url).json()
    for node_d in resp['msg']:
        if node_d['id'] == 997:  # FIXME need a better place to document this :/
            node_d['name'] = 'allen mouse brain atlas parcellation root'
            node_d['safe_name'] = 'allen mouse brain atlas parcellation root'
            node_d['acronym'] = 'mbaroot'
        ident = new_graph.namespaces['MBA'][str(node_d['id'])]
        cls = infixowl.Class(ident, graph=new_graph.g)
        cls.subClassOf = [superclass]
        parent = node_d['parent_structure_id']
        if parent:
            parent = new_graph.namespaces['MBA'][str(parent)]
            #add_hierarchy(new_graph.g, parent, rdflib.URIRef('http://uri.interlex.org/base/proper_part_of'), cls)
            add_hierarchy(new_graph.g, parent, rdflib.URIRef('http://purl.obolibrary.org/obo/BFO_0000050'), cls)

        for t in aba_trips(node_d):
            new_graph.add_node(*t)

    new_graph.write(delay=True)
    return ontid

class cocomac(rowParse):
    superclass = rdflib.URIRef('http://uri.interlex.org/base/ilx_cocomac_parc_region')
    def __init__(self, graph, rows, header):
        self.g = graph
        super().__init__(rows, header)#, order=[0])

    def ID(self, value):
        self.identifier = 'cocomac:' + value  # safe because reset every row (ish)
        self.g.add_node(self.identifier, rdflib.RDF.type, rdflib.OWL.Class)
        self.g.add_node(self.identifier, rdflib.RDFS.subClassOf, self.superclass)

    def Key(self, value):
        pass

    def Summary(self, value):
        pass

    def Acronym(self, value):
        self.g.add_node(self.identifier, 'OBOANN:acronym', value)

    def FullName(self, value):
        self.g.add_node(self.identifier, rdflib.RDFS.label, value)

    def LegacyID(self, value):
        if value:  # FIXME should fix in add_node
            self.g.add_node(self.identifier, 'OBOANN:acronym', value)

    def BrainInfoID(self, value):
        pass

def cocomac_make():
    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/generated/'
    filename = 'cocomacslim'
    ontid = ONT_PATH + filename + '.ttl'
    PREFIXES = {
        'ilx':'http://uri.interlex.org/base/',
        'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        'cocomac':'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT%20*%20from%20BrainMaps_BrainSiteAcronyms%20where%20ID=',  # looking for better options
    }
    new_graph = makeGraph(filename, PREFIXES)
    new_graph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
    new_graph.add_node(ontid, rdflib.RDFS.label, 'CoCoMac terminology')
    new_graph.add_node(ontid, rdflib.RDFS.comment, 'This file is automatically generated from the CoCoMac database on the terms from BrainMaps_BrainSiteAcronyms.')
    new_graph.add_node(ontid, rdflib.OWL.versionInfo, TODAY)
    meta = PScheme(cocomac.superclass,
                   'CoCoMac terminology parcellation concept',
                   'NCBITaxon:9544',
                   'various',
                   'problem')  # problems detected :/
    add_scheme(new_graph, meta)
    #new_graph.add_node(cocomac.superclass, rdflib.RDFS.label, 'CoCoMac terminology brain region')
    #new_graph.add_node(cocomac.superclass, rdflib.RDFS.subClassOf, PARC_SUPER[0])

    #url = 'http://cocomac.g-node.org/services/search_wizard.php?T=BrainMaps_BrainSiteAcronyms&x0=&limit=3000&page=1&format=json'
    #resp = json.loads(requests.get(url).json())  # somehow everything is double escaped :x
    url = 'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT * from BrainMaps_BrainSiteAcronyms;&format=json'
    #url = 'http://cocomac.g-node.org/services/custom_sql_query.php?sql=SELECT%20*%20from%20BrainMaps_BrainSiteAcronyms;&format=json'
    #tab_name = resp['resultTable']
    #table = resp['tables'][tab_name]
    table = requests.get(url).json()
    fields = table['fields']
    data = table['data']
    #rows = sorted(data.values())
    cocomac(new_graph, data.values(), fields)

    new_graph.write(delay=True)
    return ontid

def fmri_atlases():
    ATLAS_PATH = '/usr/share/fsl/data/atlases/'
    ONT_PATH = 'http://ontology.neuinfo.org/NIF/ttl/generated/'

    # ingest the structured xml files and get the name of the atlas/parcellation scheme
    # ingest the labels
    # for each xml files/set of nii files generate a ttl file

    ontids = []
    for xmlfile in glob.glob(ATLAS_PATH + '*.xml'):
        tree = etree.parse(xmlfile)
        name = tree.xpath('header//name')[0].text

        filename = os.path.splitext(os.path.basename(xmlfile))[0]
        ontid = ONT_PATH + filename + '.ttl'
        PREFIXES = {
            '':ontid+'/',
            'ilx':'http://uri.interlex.org/base/',
            'skos':'http://www.w3.org/2004/02/skos/core#',
            'NCBITaxon':'http://purl.obolibrary.org/obo/NCBITaxon_',
            'OBOANN':'http://ontology.neuinfo.org/NIF/Backend/OBO_annotation_properties.owl#',  # FIXME needs to die a swift death
        }
        new_graph = makeGraph(filename, PREFIXES)
        new_graph.add_node(ontid, rdflib.RDF.type, rdflib.OWL.Ontology)
        new_graph.add_node(ontid, rdflib.RDFS.label, name)
        new_graph.add_node(ontid, rdflib.RDFS.comment, 'This file is automatically generated from the %s file in the FSL atlas collection.' % xmlfile)
        new_graph.add_node(ontid, rdflib.OWL.versionInfo, TODAY)

        meta = PScheme('ilx:placeholder_' + name.replace(' ','_'),
                       name + ' parcellation concept',
                       'NCBITaxon:9606',
                       'adult',
                       'http://fsl.fmrib.ox.ac.uk/fsl/fslwiki/Atlases')  # problems detected :/
        add_scheme(new_graph, meta)

        sn = tree.xpath('header//shortname')
        if sn:
            new_graph.add_node(ontid, rdflib.namespace.SKOS.altLabel, sn[0].text)

        #tree.xpath('header//shortname').text
        for node in tree.xpath('data//label'):
            id_ = ':' + node.get('index')
            label = node.text
            new_graph.add_node(id_, rdflib.RDFS.subClassOf, meta.curie)
            new_graph.add_node(id_, rdflib.RDF.type, rdflib.OWL.Class)
            new_graph.add_node(id_, rdflib.RDFS.label, label)
        #print([(l.get('index'),l.text) for l in tree.xpath('data//label')])
        new_graph.write(delay=True)
        ontids.append(ontid)

    #embed()
    return ontids

def main():
    oper = makeGraph('', {})
    oper.reset_writeloc()
    fs = fmri_atlases()
    c = cocomac_make()
    m = mouse_brain_atlas()
    fs.extend([c, m])
    parcellation_schemes(fs)
    oper.owlapi_conversion()

    # make a protege catalog file to simplify life
    uriline = '  <uri id="User Entered Import Resolution" name="{ontid}" uri="{filename}"/>'
    xmllines = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
    '<catalog prefer="public" xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">',] + \
    [uriline.format(ontid=f, filename=f.rsplit('/',1)[-1]) for f in fs] + \
    ['  <group id="Folder Repository, directory=, recursive=true, Auto-Update=true, version=2" prefer="public" xml:base=""/>',
    '</catalog>',]
    xml = '\n'.join(xmllines)
    with open('/tmp/catalog-v001.xml','wt') as f:
        f.write(xml)

    # be sure to run
    # find -name '*.ttl.ttl' -exec sh -c 'a=$(echo "$0" | sed -r "s/.ttl$//") && mv "$0" "$a"' {}  \;
    # to move the converted files

if __name__ == '__main__':
    main()

