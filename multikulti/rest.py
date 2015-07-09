#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright Konrad Kozak kk292478@students.mimuw.edu.pl 2015/06/14 - 2015/07/01

import os
import urllib2
import gzip
import re
import json

from multikulti import app
from flask import jsonify, request
from config import query_db
from StringIO import StringIO
from multikulti_modules.parsePDB import PdbParser
from views import gunzip, unique_id, cluster_stats, alphanum_key
from glob import glob

# tylko status
@app.route('/REST/status/<string:job_id>', methods=['GET'])
def status(job_id):
    todel = str(app.config['DELETE_USER_JOBS_AFTER'])
    if request.method == 'POST' and request.json:
        id = job_id
        system_info = query_db("SELECT ligand_sequence, receptor_sequence, \
        status_date, date_add(status_date, interval  %s day) del, \
        ligand_chain, status_init status_change, project_name, status, \
        ligand_ss, ss_psipred FROM user_queue \
        WHERE jid=%s", [todel, id], one=True)

        if not system_info:
            return jsonify({
                'id': id,
                'status': 'error'})
        else:
            return jsonify({
                'status': system_info['status']})
    else:
        return jsonify({
            'status': 'error'})


# wszystko z user_quere
@app.route('/REST/job_info/<string:job_id>', methods=['GET'])
def job_info(job_id):
    todel = str(app.config['DELETE_USER_JOBS_AFTER'])
    if request.method == 'POST' and request.json:
        id = job_id
        system_info = query_db("SELECT ligand_sequence, receptor_sequence, \
        status_date, date_add(status_date, interval  %s day) del, \
        ligand_chain, status_init status_change, project_name, status, \
        ligand_ss, ss_psipred FROM user_queue \
        WHERE jid=%s", [todel, id], one=True)

        flexible = query_db("SELECT constraint_definition FROM constraints WHERE jid=%s", [id])
        excluded = query_db("SELECT excluded_region FROM excluded WHERE jid=%s", [id])

        system_info['flexible'] = map(lambda x: x['constraint_definition'], flexible)
        system_info['excluded'] = map(lambda x: x['excluded_region'], excluded)

        if not system_info:
            return jsonify({
                'id': id,
                'status': 'error'})
        else:
            return jsonify(system_info)
    else:
        return jsonify({
            'status': 'error'})


# pobranie pelnych wynikow
@app.route('/REST/job_results_all/<string:jid>', methods=['GET', 'POST'])
def get_job_all(jid):
    todel = str(app.config['DELETE_USER_JOBS_AFTER'])

    system_info = query_db("SELECT ligand_sequence, receptor_sequence, \
        status_date, date_add(status_date, interval  %s day) del, \
        ligand_chain, status_init status_change, project_name, status, \
        ligand_ss, ss_psipred FROM user_queue \
        WHERE jid=%s", [todel, jid], one=True)

    if not system_info:
        return jsonify({
            'status': 'error'})

    models = {'models': [], 'clusters': [], 'replicas': []}
    udir_path = os.path.join(app.config['USERJOB_DIRECTORY'], jid)

    clust_details = cluster_stats(jid)

    for d in ['models', 'replicas', 'clusters']:
        tm = [fil.split("/")[-1] for fil in glob(udir_path + "/" + d + "/*.gz")]
        models[d] = sorted(tm, key=alphanum_key)

    range_list = xrange(0, 10)
    if request.method == 'POST' and request.json:
        value = request.json.get('filter')  # po cluster_stats
        min = request.json.get('min')
        max = request.json.get('max')
        if value and min and max:
            filtered_results = filter(lambda x: float(x[value]) > float(min) and float(x[value]) <= float(max),
                                      clust_details)
            range_list = map(lambda x: x['id'], filtered_results)

    results = []
    for i in range_list:
        path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                                "models", models['models'][i])
        with gzip.open(path_dir) as data:
            file_content_model = data.read()

        path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                                "clusters", models['clusters'][i])
        with gzip.open(path_dir) as data:
            file_content_cluster = data.read()

        path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                                "replicas", models['replicas'][i])
        with gzip.open(path_dir) as data:
            file_content_replica = data.read()

        results.append({
            'jobid': jid,
            'info': system_info,
            'model': i + 1,
            'model_data': file_content_model,
            'cluster_data': file_content_cluster,
            'trajectory_data': file_content_replica,
            'cluster_density': clust_details[i]["density"],
            'average_rmsd': clust_details[i]["rmsd"],
            'max_rmsd': clust_details[i]["maxrmsd"],
            'elements': clust_details[i]["counts"]
        })

    result = {'models': results}

    return jsonify(result)


@app.route('/REST/job_results/<string:jid>', methods=['GET', 'POST'])
def get_job(jid):


    todel = str(app.config['DELETE_USER_JOBS_AFTER'])

    system_info = query_db("SELECT ligand_sequence, receptor_sequence, \
            status_date, date_add(status_date, interval  %s day) del, \
            ligand_chain, status_init status_change, project_name, status, \
            ligand_ss, ss_psipred FROM user_queue \
            WHERE jid=%s", [todel, jid], one=True)

    if not system_info:
        return jsonify({
            'status': 'error'})

    models = {'models': [], 'clusters': [], 'replicas': []}
    udir_path = os.path.join(app.config['USERJOB_DIRECTORY'], jid)

    clust_details = cluster_stats(jid)

    for d in ['models']:
        tm = [fil.split("/")[-1] for fil in glob(udir_path + "/" + d + "/*.gz")]
        models[d] = sorted(tm, key=alphanum_key)

    range_list = xrange(0, 10)
    if request.method == 'POST' and request.json:
        value = request.json.get('filter')  # po cluster_stats
        min = request.json.get('min')
        max = request.json.get('max')
        if value and min and max:
            filtered_results = filter(lambda x: float(x[value]) > float(min) and float(x[value]) <= float(max),
                                      clust_details)
            range_list = map(lambda x: x['id'], filtered_results)

    results = []
    for i in range_list:
        path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                                "models", models['models'][i])
        with gzip.open(path_dir) as data:
            file_content_model = data.read()

        results.append({
            'jobid': jid,
            'info': system_info,
            'model': i + 1,
            'model_data': file_content_model,
            'cluster_density': clust_details[i]["density"],
            'average_rmsd': clust_details[i]["rmsd"],
            'max_rmsd': clust_details[i]["maxrmsd"],
            'elements': clust_details[i]["counts"]
        })

    result = {'models': results}

    return jsonify(result)


@app.route('/REST/get_cluster/<string:jid>/<string:model_id>', methods=['GET', 'POST'])
def get_cluster(jid,model_id):

    model_id = int(model_id)
    clust_details = cluster_stats(jid)

    cluster_name = "cluster_%s.pdb.gz" %model_id
    path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                            "clusters", cluster_name)
    with gzip.open(path_dir) as data:
        file_content_cluster = data.read()

    results = []
    results.append({
        'jobid': jid,
        'cluster_data': file_content_cluster,
        'cluster_density': clust_details[model_id]["density"],
        'average_rmsd': clust_details[model_id]["rmsd"],
        'max_rmsd': clust_details[model_id]["maxrmsd"],
        'elements': clust_details[model_id]["counts"]
    })

    result = {'model': results}

    return jsonify(result)

#dziala okej przez curla
@app.route('/REST/get_trajectory/<string:jid>/<string:trajectory_id>', methods=['GET', 'POST'])
def get_trajectory(jid,trajectory_id):

    trajectory_id = int(trajectory_id)
    trajectory_name = "replica_%s.pdb.gz" %trajectory_id

    path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                            "replicas", trajectory_name)
    with gzip.open(path_dir) as data:
        file_content_replica = data.read()

    results = []
    results.append({
        'jobid': jid,
        'trajectory': file_content_replica,
    })

    result = {'model': results}

    return jsonify(result)


def get_model(content, model_idx):
    te = re.compile(r'MODEL.{6,8}' + str(model_idx) + '.*?ENDMDL', flags=re.DOTALL)
    out = te.search(content).group(0)
    return out


@app.route('/REST/trajectory/<string:jid>/<string:model>/<int:start>/<int:end>', methods=['GET', 'POST'])
def get_selected_trajectory(jid, model, start, end):
    replicas = []
    path_dir = os.path.join(app.config['USERJOB_DIRECTORY'], jid,
                            "replicas", 'replica_' + model + '.pdb.gz')

    if start and end:
        with gzip.open(path_dir) as data:
            content = data.read()
        for i in xrange(start, end + 1):
            dict = {'result_no': model, 'model': i, 'trajectory': get_model(content, i)}
            replicas.append(dict)

    result = {'models': replicas}
    return jsonify(result)


@app.route('/REST/add_job/', methods=['GET', 'POST'])
def add_job():
    if request.method == 'POST':
        receptor_file = request.files.get('file')
        try:
            if request.json is not None:
                data = prepare_data(request.json, receptor_file)
            elif 'data' in request.form:
                data = prepare_data(json.loads(request.form['data']), receptor_file)
            else:
                data = prepare_data(request.form, receptor_file)
        except RestValidationError as e:
            return jsonify({'error': e.message})
        result, jid = add_data_to_db(data)
        add_excluded(data, jid)
        user_add_constraints(data, jid)

        return jsonify({
            'jid': jid})


def prepare_data(data, receptor_file):
    validate_data(data, receptor_file)
    # przypisanie wstepnych wartosci
    data['receptor_pdb_code'] = data.get('receptor_pdb_code', '')
    data['receptor_file'] = receptor_file
    data['ligand_seq'] = ''.join(data.get('ligand_seq', '').upper().replace(' ', '').split())
    data['ligand_ss'] = ''.join(data.get('ligand_ss', '').upper().replace(' ', '').split())
    data['simulation_cycles'] = int(data.get('simulation_cycles', 50))
    data['project_name'] = data.get('project_name', '')
    data['email'] = data.get('email', '')
    data['show'] = json_bool_to_db(data.get('show_job'))
    data['excluded_regions'] = data.get('excluded_regions', [])
    data['constraints'] = data.get('constraints', [])
    data['scaling_factor'] = data.get('overall_weight', '1.0')

    return data


def check_range(file, constraints, excluded):
    values_by_chain = {}
    for match in re.findall(r'ATOM\s+\d+\s+\w+\s+\w+\s+([A-Z])\s+(\d+)', file.read()):
        chain = match[0]
        val = int(match[1])
        if chain not in values_by_chain:
            values_by_chain[chain] = [val, val]
        else:
            values_by_chain[chain][0] = min(values_by_chain[chain][0], val)
            values_by_chain[chain][1] = max(values_by_chain[chain][1], val)

    for i in constraints:
        if i['chain'] not in values_by_chain:
            raise RestValidationError('Selected chain (%s) not exist' % i["chain"])
        if int(i['start']) < values_by_chain[i['chain']][0] or int(i['end']) > values_by_chain[i['chain']][1]:
            raise RestValidationError('Selected region out of receptor range for chain %s' % i['chain'])

    for i in excluded:
        if i['chain'] not in values_by_chain:
            raise RestValidationError('Selected chain (%s) not exist' % i["chain"])
        if int(i['start']) < values_by_chain[i['chain']][0] or int(i['end']) > values_by_chain[i['chain']][1]:
            raise RestValidationError('Selected region out of receptor for chain %s' % i['chain'])

    return True


def json_bool_to_db(data):
    if isinstance(data, bool):
        return data
    if data is None:
        return 0
    if str(data).lower() == "true":
        return 1
    else:
        return 0


def add_data_to_db(data):
    jid = unique_id()

    if data['receptor_file'] != None:
        pdb = get_PDB_from_file(jid, data['receptor_file'])
    else:
        pdb = get_PDB_file(data['receptor_pdb_code'], jid)

    return (query_db("INSERT INTO user_queue(jid, email, receptor_sequence, \
         ligand_sequence, ligand_ss, hide, project_name,simulation_length) \
         VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", [jid, data['email'], pdb,
                                            data['ligand_seq'], data['ligand_ss'], data['show'], data['project_name'],
                                            data['simulation_cycles']], insert=True), jid)


def get_PDB_file(pdb_code, jid):
    dest_directory = os.path.join(app.config['USERJOB_DIRECTORY'], jid)
    dest_file = os.path.join(dest_directory, "input.pdb.gz")
    os.mkdir(dest_directory)

    d = pdb_code.split(":")
    pdbcode = d[0]
    if len(d) > 1:
        chain = d[1]
    else:
        chain = ''

    buraki = urllib2.urlopen('http://www.rcsb.org/pdb/files/' + pdbcode + '.pdb.gz')
    b2 = buraki.read()
    ft = StringIO(b2)
    with gzip.GzipFile(fileobj=ft, mode="rb") as f:
        p = PdbParser(f, chain=chain)
        receptor_seq = p.getSequence()
        p.savePdbFile(dest_file)
        gunzip(dest_file)

    buraki.close()

    return receptor_seq


def get_PDB_from_file(jid, file):
    dest_directory = os.path.join(app.config['USERJOB_DIRECTORY'], jid)
    dest_file = os.path.join(dest_directory, "input.pdb.gz")
    os.mkdir(dest_directory)

    p = PdbParser(file)
    receptor_seq = p.getSequence()
    p.savePdbFile(dest_file)
    gunzip(dest_file)

    if len(receptor_seq) > 500:
        raise RestValidationError('Max protein size: 500 residues')

    return receptor_seq


def add_excluded(data, jid):
    for i in data['excluded_regions']:
        normal = i['start'] + ':' + i['chain'] + ' ' + '-' + ' ' + i['end'] + ':' + i['chain']
        jmol = i['start'] + '-' + i['end'] + ':' + i['chain']
        query_db("INSERT INTO excluded(jid,excluded_region, excluded_jmol) \
                VALUES(%s,%s,%s)", [jid, normal, jmol], insert=True)
    return True


def user_add_constraints(data, jid):
    query_db("UPDATE user_queue SET constraints_scaling_factor=%s \
            WHERE jid=%s", [data['scaling_factor'], jid], insert=True)

    for i in data['constraints']:
        constraint_definition = i['start'] + ':' + i['chain'] + ' ' + '-' + ' ' + i['end'] + ':' + i['chain']
        force = i['weight']
        constraint_jmol = i['start'] + '-' + i['end'] + ':' + i['chain']
        query_db("INSERT INTO constraints(`jid`,`constraint_definition`,`force`,\
                `constraint_jmol`) VALUES(%s,%s,%s,%s)", [jid, constraint_definition, force, constraint_jmol],
                 insert=True)
    return True


def validate_data(data, receptor_file):
    check_range(receptor_file, data['constraints'], data['excluded_regions'])
    validate_name(data.get('project_name'))
    validate_receptor_file(receptor_file)
    validate_pdb_input(data.get('receptor_pdb_code'), receptor_file)
    validate_ligand_seq(data.get('ligand_seq'))
    validate_ligand_ss(data.get('ligand_ss'))
    if 'ligand_ss' in data:
        validate_eqlen(data['ligand_seq'], data['ligand_ss'])
    validate_email(data.get('email'))
    validate_simulation_cycles(data.get('simulation_cycles'))


def validate_name(name):
    if name is None:
        return
    validate_length(name, 4, 150)


def validate_receptor_file(receptor_file):
    if receptor_file is None:
        return
    if '.' not in receptor_file.filename \
            or receptor_file.filename.rsplit('.', 1)[1] not in app.config['ALLOWED_EXTENSIONS']:
        raise RestValidationError('PDB file format only!')


def validate_pdb_input(pdb_receptor, receptor_file):
    if receptor_file is not None and len(receptor_file.filename) >= 5:
        validate_pdb_input_file(receptor_file)
    elif pdb_receptor is not None:
        validate_pdb_input_code(pdb_receptor)
    else:
        raise RestValidationError('Protein PDB code or PDB file is required')


def validate_pdb_input_file(receptor_file):
    p = PdbParser(receptor_file.stream)
    check_pdb_input(p)


def validate_pdb_input_code(pdb_receptor):
    if len(pdb_receptor) < 4:
        raise RestValidationError('Protein code must be 4-letter (2PCY) or >5 \
                letters (2PCY:A or 2PCY:AB ...). Leave empty only if PDB \
                file is provided')
    d = pdb_receptor.split(":")
    if len(d) > 1:
        chain = d[1]
    else:
        chain = ''
    pdb_code = d[0]

    buraki = urllib2.urlopen('http://www.rcsb.org/pdb/files/' + pdb_code + '.pdb.gz')
    b2 = buraki.read()
    ft = StringIO(b2)

    with gzip.GzipFile(fileobj=ft, mode="rb") as f:
        p = PdbParser(f, chain=chain)
        check_pdb_input(p, allow_space=True)

    buraki.close()


def check_pdb_input(p, allow_space=False):
    missing = p.getMissing()
    seq = p.getSequence()
    allowed_seq = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M',
                   'N', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'Y']
    if allow_space:
        allowed_seq.append(' ')
    for e in seq:
        if e not in allowed_seq:
            raise RestValidationError('Non-standard residue in the receptor \
                                   structure')
    if len(p.getBody()) < 16 or len(seq) == 0:
        raise RestValidationError('File without chain or chain shorter than \
                               4 residues')
    if len(seq) > 500:
        raise RestValidationError('CABS-dock allows max 500 receptor residues. \
                               Provided file contains %d' % len(seq))
    if missing > 5:
        raise RestValidationError('Missing atoms within receptor (M+N = %d). \
                Protein must fullfill M+N<6, where M - number of chains, \
                N - number of breaks' % missing)


def validate_ligand_seq(ligand_seq):
    if ligand_seq is None:
        raise RestValidationError('Missing peptide sequence')
    validate_length(ligand_seq, 4, 30)
    validate_sequence(ligand_seq)


def validate_sequence(field):
    allowed_seq = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N',
                   'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'Y']
    for letter in re.sub("\s", "", field):
        if letter not in allowed_seq:
            raise RestValidationError('Sequence contains non-standard aminoacid symbol: %s' % letter)


def validate_ligand_ss(ligand_ss):
    if ligand_ss is None:
        return
    validate_length(ligand_ss, 4, 30)
    validate_ss(ligand_ss)


def validate_ss(field):
    allowed_seq = ['C', 'H', 'E']
    for letter in re.sub("\s", "", field):
        if letter not in allowed_seq:
            raise RestValidationError('Secondary structure contains non-standard \
                    symbol: %s. <br><small>Allowed H - helix, \
                    E - extended/beta, C - coil.</small>' % letter)


def validate_eqlen(first_field, second_field):
    if len(first_field) != len(second_field):
        raise RestValidationError('Secondary structure length != ligand sequence length')


def validate_email(email):
    if email is None:
        return
    match = re.search(r'^.+@([^.@][^@]+)$', email, re.IGNORECASE)
    if match is None:
        raise RestValidationError('Invalid email address: %s' % email)


def validate_simulation_cycles(length):
    if length is None:
        return
    try:
        length = int(length)
    except ValueError:
        raise RestValidationError('Simulation cycles must be an integer')
    if length < 5 or length > 200:
        raise RestValidationError('Simulation cycles not in range (%d, %d)' % (5, 200))


def validate_length(field, min=None, max=None):
    if min is not None and len(field) < min:
        raise RestValidationError('Field \'%s\' is shorter than %d characters' % (field, min))
    if max is not None and len(field) > max:
        raise RestValidationError('Field \'%s\' is longer than %d characters' % (field, max))


class RestValidationError(Exception):
    pass
