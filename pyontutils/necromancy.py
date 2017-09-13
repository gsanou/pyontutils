#!/usr/bin/env python3.6
"""Find dead ids in an ontology and raise them to be owl:Classes again.
Also build a list of classes that may be banished to the shadow realm
of oboInOwl:hasAlternativeId in the near future.

Usage:
    necromancy [options] <file>...

Options:
    -h --help       print this
    -v --verbose    do something fun!
    -s --slow       do not use a process pool
    -n --nowrite    parse the file and reserialize it but do not write changes

"""

import os
import rdflib
from docopt import docopt
from pyontutils.utils import makePrefixes, makeGraph, createOntology, anyMembers, rdf, rdfs, owl, oboInOwl

def kludge(filepath):
    if 'doid' in filepath:
        return 'DOID',
    elif 'uberon' in filepath:
        return 'UBERON',
    elif 'go' in filepath:
        return 'GO',
    elif 'pr' in filepath:
        return 'PR',
    elif 'ero' in filepath:
        return 'ERO',
    elif 'pato' in filepath:
        return 'PATO',
    elif 'so' in filepath:
        return 'SO',
    else:
        raise NameError('We don\' know what to do with identifers from %s' % filepath)

def alreadyHasEntry(oldClassString, og):
    """ Return true if there is already an owl:Class with the old id"""
    namespace = oldClassString.split(':')[0]
    if namespace == 'http':
        target = rdflib.URIRef(oldClassString)
        print('OLD CLASS ID IS A URL', oldClassString)
    else:
        try:
            og.add_known_namespace(namespace)
            target = og.expand(oldClassString)
        except KeyError:
            print('MISSING NAMESPACE', namespace, oldClassString)
            return True  # we only want known namespaces
    return (target, rdf.type, owl.Class) in og.g

def load(file):
    filepath = os.path.expanduser(file)
    _, ext = os.path.splitext(filepath)
    filetype = ext.strip('.')
    if filetype == 'ttl':
        infmt = 'turtle'
    else:
        infmt = None
    print(filepath)
    graph = rdflib.Graph()
    try:
        graph.parse(filepath, format=infmt)
    except rdflib.plugins.parsers.notation3.BadSyntax as e:
        print('PARSING FAILED', filepath)
        raise e
    og = makeGraph('', graph=graph)

    # FIXME this should really just be a function :/
    curie, *prefs = kludge(filepath)

    name = os.path.splitext(os.path.basename(filepath))[0]
    version = list(graph.subject_objects(owl.versionIRI))[0][1]

    ng = createOntology(f'{name}-dead',
                        f'NIF {curie} deprecated',
                        makePrefixes('replacedBy', 'NIFRID', curie, *prefs),
                        f'{name}dead',
                        f'Classes from {curie} with owl:deprecated true that we want rdfs:subClassOf NIFRID:birnlexRetiredClass, or classes hiding in a oboInOwl:hasAlternativeId annotation. This file was generated by pyontutils/necromancy from {version}.')
    extract(og, ng, curie)

def extract(og, ng, curie):
    graph = og.g
    properties = (owl.AnnotationProperty, owl.DatatypeProperty, owl.ObjectProperty)
    deads = [s for s in graph.subjects(owl.deprecated, rdflib.Literal(True))]
    for s in deads:
        types = set(o for o in graph.objects(s, rdf.type))
        if anyMembers(types, *properties):
            p, o = rdfs.subPropertyOf, owl.DeprecatedProperty
        elif owl.Class in types:
            p, o = rdfs.subClassOf, owl.DeprecatedClass
        else:
            continue  # don't bother with named individuals

        trip = (ng.check_thing(s), ng.check_thing(p), ng.check_thing(o))
        if trip not in og.g:
            ng.g.add(trip)

    # TODO cases where owl:deprecated is not used but sco owl:DeprecatedClass is...

    base_alts = list(graph.subject_objects(oboInOwl.hasAlternativeId))
    for replacedByClass, oldClassString in base_alts:
        if curie + ':' in oldClassString or curie + '_' in oldClassString:
            oldClassString = oldClassString.toPython()
            s = ng.check_thing(oldClassString)
            if s not in deads:
                types = set(o for o in graph.objects(replacedByClass, rdf.type))
                if anyMembers(types, *properties):
                    p, o = rdfs.subPropertyOf, owl.DeprecatedProperty
                elif owl.Class in types:
                    p, o = rdfs.subClassOf, owl.DeprecatedClass
                else:
                    continue  # don't bother with named individuals
                [ng.add_trip(s, rdf.type, o) for o in types]
                ng.add_trip(s, p, o)
                ng.add_trip(s, owl.deprecated, True)
                ng.add_trip(s, 'replacedBy:', replacedByClass)
    
    ng.write()

def main():
    from joblib import Parallel, delayed
    args = docopt(__doc__, version = "necromancy 0.5")
    if args['--slow'] or len(args['<file>']) == 1:
        [load(f) for f in args['<file>']]
    else:
        Parallel(n_jobs=9)(delayed(load)(f) for f in args['<file>'])

if __name__ == '__main__':
    main()
