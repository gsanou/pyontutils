#!/usr/bin/env python3.6
import csv
from pathlib import Path
import rdflib
from pyontutils.neuron_models.compiled import neuron_data_lifted
ndl_neurons = neuron_data_lifted.Neuron.neurons()
from pyontutils.neuron_models.compiled import basic_neurons
bn_neurons = basic_neurons.Neuron.neurons()
from pyontutils.utils import byCol, relative_path
from pyontutils.core import resSource, interlex_namespace
from pyontutils.config import devconfig
# import these last so that graphBase resets (sigh)
from pyontutils.neuron_lang import *
from pyontutils.neurons import *
from IPython import embed

# TODO
# 1. inheritance for owlClass from python classes
# 2. add ttl serialization for subclasses of EBM
# 3. pv superclass for query example

class NeuronSWAN(NeuronEBM):
    owlClass = 'ilxtr:NeuronSWAN'

rename_rules = {'Colliculus inferior': 'Inferior colliculus',
                'Colliculus superior': 'Superior colliculus',
                'Premammillary nucleus dorsal': 'Dorsal premammillary nucleus',
                'Premammillary nucleus ventral': 'Ventral premammillary nucleus',
                'Septal complex lateral': 'Lateral septal complex',
                'Septal complex medial': 'Medial septal complex',
                'Substantia nigra pars reticulata': 'Reticular part of substantia nigra',
                'Thalamic reticular nucleus': 'Reticular thalamic nucleus',
                'Trigeminal nerve motor nucleus': 'Motor nucleus of trigeminal nerve',
                'Trigeminal nerve principal sensory nucleus': 'Principal sensory nucleus of trigeminal nerve'}

def main():
    resources = Path(__file__).resolve().absolute().parent.parent / 'resources'
    cutcsv = resources / 'common-usage-types.csv'
    with open(cutcsv.as_posix(), 'rt') as f:
        rows = [l for l in csv.reader(f)]

    bc = byCol(rows)

    labels, *_ = zip(*rows)
    sls0 = set(labels)
    ns = []
    for n in ndl_neurons:
        l = n._origLabel
        for replace, match in rename_rules.items():  # HEH
            l = l.replace(match, replace)
        if l in labels:
            n._origLabel = l
            ns.append(n)

    sns = set(n._origLabel for n in ns)

    sls1 = sls0 - sns

    agen = [c.label for c in bc if c.Autogenerated]
    sagen = set(agen)
    ans = []
    sans = set()
    missed = set()
    for n in bn_neurons:
        # can't use capitalize here because there are proper names that stay uppercase
        l = n.label.replace('(swannt) ',
                            '').replace('Intrinsic',
                                        'intrinsic').replace('Projection',
                                                             'projection')
        for replace, match in rename_rules.items():  # HEH
            l = l.replace(match, replace)

        if l in agen:
            n._origLabel = l
            ans.append(n)
            sans.add(l)
        else:
            missed.add(l)

    agen_missing = sagen - sans
    sls2 = sls1 - sans

    nlx = [c.label for c in bc if c.Neurolex]
    snlx = set(nlx)

    lnlx = set(n.lower() for n in snlx)
    sos = set(n._origLabel.lower() for n in ndl_neurons)
    print('neurolex missing:', len(lnlx - sos))

    progress = len(sls0), len(sls1), len(sls2)
    print('progress:', progress)

    class SourceCUT(resSource):
        sourceFile = 'pyontutils/resources/common-usage-types.csv'  # FIXME relative to git workingdir...
        source_original = True

    sources = SourceCUT(),
    swanr = rdflib.Namespace(interlex_namespace('swanson/uris/readable/'))
    Config('common-usage-types', sources=sources, source_file=relative_path(__file__),
           prefixes={'swanr':swanr,
                     'SWAN':interlex_namespace('swanson/uris/neuroanatomical-terminology/terms/'),
                     'SWAA':interlex_namespace('swanson/uris/neuroanatomical-terminology/appendix/'),})
    new = [NeuronCUT(*n.pes, label=n._origLabel, override=True) for n in ns + ans]
    # TODO preserve the names from neuronlex on import ...
    Neuron.write()
    Neuron.write_python()
    if __name__ == '__main__':
        embed()

if __name__ == '__main__':
    main()
