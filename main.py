import uuid
import random
from collections import namedtuple
import matplotlib.pyplot as plt

import pandas as pd
import simpy
import streamlit as st

receiving_times = []
processing_times = []
analyzing_times = []
reporting_times = [];
tat_times = []

TestOrder = namedtuple('TestOrder', ['ward', 'test_name', 'labno'])
TimeTracker = namedtuple('TimeTracker', ['start_t', 'finish_t', 'delta_t', 'label1', 'label2'])


def generate_random_labno(number=10):
    """Generate random lab numbers."""
    return [str(uuid.uuid4()) for i in range(number)]


st.title('MTForce: Medical Lab Workforce Simulation')
st.header('Environment Settings')

if 'machines' not in st.session_state:
    st.session_state.machines = {}

if 'tests' not in st.session_state:
    st.session_state.tests = {}

if 'num_centrifuge' not in st.session_state:
    st.session_state.num_centrifuge = 0

st.subheader('Number of Tests')

st.number_input('Enter a number of tests in this simulation:', key='num_tests')

st.subheader('Analytical Machine')

machine_name = st.text_input('Enter a machine name/model:')
throughput = st.number_input('Enter a throughput:')

if st.button('Add', key='machine'):
    st.session_state.machines[machine_name] = {'throughput': throughput, 'tests': []}
st.write(st.session_state.machines)

st.subheader('Centrifuge')
st.number_input('Enter number of centrifuge:', key='num_centrifuge')
st.number_input('Enter number of centrifuge capacity:', key='num_centrifuge_capacity')

st.subheader('Test')

test_name = st.text_input('Enter a test name:')
centrifuge_duration = st.number_input('Centrifuge duration:')
centrifuge_rounds = st.number_input('Centrifuge round:')
analytical_machines = st.multiselect('Machines', options=st.session_state.machines.keys())

if st.button('Add', key='test'):
    st.session_state.tests[test_name] = {
        'centrifuge_rounds': centrifuge_rounds,
        'centrifuge_duration': centrifuge_duration,
        'machines': analytical_machines
    }
st.write(st.session_state.tests)


num_staff = st.number_input('Enter number of staff:', value=0)

env = simpy.Environment()

staff_resource = simpy.Resource(env, capacity=num_staff)
centrifuge_resource = simpy.Resource(env, capacity=st.session_state.num_centrifuge)
machine_resources = {}
for machine_name in st.session_state.machines:
    machine = st.session_state.machines[machine_name]
    machine_resources[machine_name] = simpy.Resource(env, capacity=1)


def test(env, lab_order):
    yield env.timeout(lab_order['arriving_time'])
    lab_order_start = env.now
    start_t = env.now
    with staff_resource.request() as request:
        yield request
        yield env.timeout(random.randrange(5, 10))
        finish_t = env.now
        receiving_times.append(TimeTracker(start_t, finish_t, finish_t - start_t, '', ''))

    waiting_for_centrifuge = []
    for test_order in lab_order['test_orders']:
        if st.session_state.tests[test_order.test_name]['centrifuge_rounds']:
            waiting_for_centrifuge.append(test_order)

    start_t = env.now
    with centrifuge_resource.request() as request:
        yield request
        for i in range(int(st.session_state.tests[test_order.test_name]['centrifuge_rounds'])):
            yield env.timeout(st.session_state.tests[test_order.test_name]['centrifuge_duration'])
        finish_t = env.now
        processing_times.append(TimeTracker(start_t, finish_t, finish_t - start_t, '', ''))

    for test_order in lab_order['test_orders']:
        machine_name = random.choice(st.session_state.tests[test_order.test_name]['machines'])
        with machine_resources[machine_name].request() as request:
            start_t = env.now
            yield request
            yield env.timeout(st.session_state.machines[machine_name]['throughput'] // 60)
            finish_t = env.now
            analyzing_times.append(TimeTracker(start_t, finish_t, finish_t - start_t, test_order.test_name, machine_name))

    with staff_resource.request() as request:
        start_t = env.now
        yield request
        yield env.timeout(random.randrange(3, 10))
        finish_t = env.now
        reporting_times.append(TimeTracker(start_t, finish_t, finish_t - start_t, lab_order['labno'], ''))

    lab_order_finish = env.now
    tat_times.append((TimeTracker(lab_order_start, lab_order_finish, lab_order_finish - lab_order_start, lab_order['labno'], '')))


if st.button('Run', key='run') and num_staff > 0:
    wards = {
        'ER': 0,
        'IPD': 0,
        'OPD': 0
    }
    lab_orders = {}
    for n, labno in enumerate(generate_random_labno(int(st.session_state.num_tests)), start=1):
        ward = random.choice(list(wards.keys()))
        current_time = wards[ward]
        if current_time == 0:
            current_time = random.randrange(0, 9)
            arriving_time = current_time
        else:
            arriving_time = current_time * random.randrange(1, 3)
        lab_orders[labno] = {'arriving_time': arriving_time, 'ward': ward}

        num_test = random.randrange(1, len(st.session_state.tests) + 1)
        test_name_ordered = set()
        test_orders = []
        i = 0
        while i < num_test:
            test_name = random.choice([t for t in st.session_state.tests.keys()])
            if test_name not in test_name_ordered:
                test_order = TestOrder(ward, test_name, labno)
                i += 1
                test_name_ordered.add(test_name)
                test_orders.append(test_order)
        env.process(test(env, {'test_orders': test_orders, 'arriving_time': arriving_time, 'labno': labno}))

        lab_orders[labno]['test_orders'] = test_orders

    env.run()
    st.header('Specimens Receiving Time')
    st.write(pd.DataFrame(data=receiving_times))
    st.line_chart(pd.DataFrame(data=receiving_times), y='delta_t')
    fig, ax = plt.subplots()
    ax.hist(pd.DataFrame(data=receiving_times).delta_t, bins=20)
    st.pyplot(fig)

    st.header('Specimens Processing Time')
    st.write(pd.DataFrame(data=processing_times))
    fig, ax = plt.subplots()
    ax.hist(pd.DataFrame(data=processing_times).delta_t, bins=20)
    st.pyplot(fig)

    st.header('Analyzing Time')
    st.write(pd.DataFrame(data=analyzing_times))
    fig, ax = plt.subplots()
    ax.hist(pd.DataFrame(data=analyzing_times).delta_t, bins=20)
    st.pyplot(fig)

    st.header('TAT Time')
    st.write(pd.DataFrame(data=tat_times))

    fig, ax = plt.subplots(nrows=1, ncols=2)
    ax[0].hist(pd.DataFrame(data=tat_times).delta_t, bins=20)
    ax[1].boxplot(pd.DataFrame(data=tat_times).delta_t, notch=True)
    st.pyplot(fig)
