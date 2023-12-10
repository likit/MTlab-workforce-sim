import uuid
import random
from collections import namedtuple
import matplotlib.pyplot as plt

import pandas as pd
import simpy
import streamlit as st

APPROVAL_DURATION = [.5, 1.5]
REPORT_DURATION = [.5, 1.5]
REGISTER_DURATION = [.5, 1.5]

registration_times = []
processing_times = []
analyzing_times = []
reporting_times = []
approving_times = []
arriving_times = []
tat_times = []

TestOrder = namedtuple('TestOrder', ['ward', 'test_name', 'labno'])
TimeTracker = namedtuple('TimeTracker', ['start_t', 'finish_t', 'wait_t', 'delta_t', 'label1', 'label2'])


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

st.subheader('Number of Orders')

st.number_input('Enter a number of orders in this simulation:', key='num_orders', step=1)

st.subheader('Duration')
st.number_input('Enter a minimum registering time:', key='registering_duration_min', value=1.0)
st.number_input('Enter a maximum registering time:', key='registering_duration_max', value=2.0)

st.number_input('Enter a minimum reporting time:', key='reporting_duration_min', value=1.0)
st.number_input('Enter a maximum reporting time:', key='reporting_duration_max', value=2.0)

st.number_input('Enter a minimum approving time:', key='approving_duration_min', value=1.0)
st.number_input('Enter a maximum approving time:', key='approving_duration_max', value=2.0)

st.number_input('Enter a minimum specimens delay time:', key='delay_duration_min', value=1.0)
st.number_input('Enter a maximum specimens delay time:', key='delay_duration_max', value=2.0)

st.subheader('Analytical Machine')

machine_name = st.text_input('Enter a machine name/model:')
throughput = st.number_input('Enter a throughput:', step=1)

if st.button('Add', key='machine'):
    st.session_state.machines[machine_name] = {'throughput': throughput}
st.write(st.session_state.machines)

st.subheader('Centrifuge')
st.number_input('Enter number of centrifuge:', key='num_centrifuge', step=1)

st.subheader('Test')

test_name = st.text_input('Enter a test name:')
centrifuge_duration = st.number_input('Centrifuge duration:', step=1)
centrifuge_rounds = st.number_input('Centrifuge round:', step=1)
analytical_machines = st.multiselect('Machines', options=st.session_state.machines.keys())

if st.button('Add', key='test'):
    st.session_state.tests[test_name] = {
        'centrifuge_rounds': centrifuge_rounds,
        'centrifuge_duration': centrifuge_duration,
        'machines': analytical_machines
    }
st.write(st.session_state.tests)


num_staff = st.number_input('Enter number of staff at specimens registration:', value=0)
num_reporters = st.number_input('Enter number of staff at reporters:', value=0)
num_approvers = st.number_input('Enter number of staff at approvers:', value=0)

env = simpy.Environment()

receiver_resource = simpy.Resource(env, capacity=num_staff)
approver_resource = simpy.Resource(env, capacity=num_approvers)
reporter_resource = simpy.Resource(env, capacity=num_reporters)
centrifuge_resource = simpy.Resource(env, capacity=st.session_state.num_centrifuge)
machine_resources = {}
for machine_name in st.session_state.machines:
    machine = st.session_state.machines[machine_name]
    machine_resources[machine_name] = simpy.Resource(env, capacity=1)


def test(env, lab_order):
    yield env.timeout(lab_order['arriving_time'])
    lab_order_start = env.now
    with receiver_resource.request() as request:
        start_t = env.now
        yield request
        wait_t = env.now - start_t
        yield env.timeout(random.randrange(st.session_state.registering_duration_min, st.session_state.registering_duration_max))
        finish_t = env.now
        registration_times.append(TimeTracker(start_t, finish_t, wait_t, finish_t - start_t, lab_order['labno'], ''))

    waiting_for_centrifuge = []
    for test_order in lab_order['test_orders']:
        if st.session_state.tests[test_order.test_name]['centrifuge_rounds']:
            waiting_for_centrifuge.append(test_order)

    if waiting_for_centrifuge:
        with centrifuge_resource.request() as request:
            start_t = env.now
            yield request
            wait_t = env.now - start_t
            for i in range(int(st.session_state.tests[test_order.test_name]['centrifuge_rounds'])):
                yield env.timeout(st.session_state.tests[test_order.test_name]['centrifuge_duration'])
            finish_t = env.now
            processing_times.append(TimeTracker(start_t, finish_t, wait_t, finish_t - start_t, '', ''))

    for test_order in lab_order['test_orders']:
        machine_name = random.choice(st.session_state.tests[test_order.test_name]['machines'])
        yield env.timeout(random.randrange(st.session_state.delay_duration_min, st.session_state.delay_duration_max))
        with machine_resources[machine_name].request() as request:
            start_t = env.now
            yield request
            wait_t = env.now - start_t
            yield env.timeout(1 / (st.session_state.machines[machine_name]['throughput'] / 60))
            finish_t = env.now
            analyzing_times.append(TimeTracker(start_t, finish_t, wait_t, finish_t - start_t, test_order.test_name, machine_name))

    with reporter_resource.request() as request:
        start_t = env.now
        yield request
        wait_t = env.now - start_t
        yield env.timeout(random.randrange(st.session_state.reporting_duration_min, st.session_state.reporting_duration_max))
        finish_t = env.now
        reporting_times.append(TimeTracker(start_t, finish_t, wait_t, finish_t - start_t, lab_order['labno'], ''))

    with approver_resource.request() as request:
        start_t = env.now
        yield request
        wait_t = env.now - start_t
        yield env.timeout(random.randrange(st.session_state.approving_duration_min, st.session_state.approving_duration_max))
        finish_t = env.now
        approving_times.append(TimeTracker(start_t, finish_t, wait_t, finish_t - start_t, lab_order['labno'], ''))

    lab_order_finish = env.now
    tat_times.append((TimeTracker(lab_order_start, lab_order_finish, None, lab_order_finish - lab_order_start, lab_order['labno'], '')))


if st.button('Run', key='run') and num_staff > 0:
    wards = {
        'ER': 0,
        'IPD': 0,
        'OPD': 0
    }
    lab_orders = {}
    arriving_time = 1
    for n, labno in enumerate(generate_random_labno(int(st.session_state.num_orders)), start=1):
        ward = random.choice(list(wards.keys()))
        if arriving_time > 10:
            arriving_time += random.randrange(-10, 20)
        else:
            arriving_time += random.randrange(0, 20)
        arriving_times.append(arriving_time)
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

    st.header('Specimens Registration Time')
    st.write(pd.DataFrame(data=registration_times))
    st.write(pd.DataFrame(data=registration_times).describe())
    # fig, ax = plt.subplots()
    # ax.boxplot(pd.DataFrame(data=registration_times).delta_t, notch=True)
    # st.pyplot(fig)

    st.header('Specimens Processing Time')
    st.write(pd.DataFrame(data=processing_times))
    st.write(pd.DataFrame(data=processing_times).describe())
    # fig, ax = plt.subplots()
    # ax.boxplot(pd.DataFrame(data=processing_times).delta_t, notch=True)
    # st.pyplot(fig)

    st.header('Analyzing Time')
    st.write(pd.DataFrame(data=analyzing_times))
    st.write(pd.DataFrame(data=analyzing_times).describe())
    # fig, ax = plt.subplots()
    # ax.boxplot(pd.DataFrame(data=analyzing_times).delta_t, notch=True)
    # st.pyplot(fig)

    st.header('Reporting Time')
    st.write(pd.DataFrame(data=reporting_times))
    st.write(pd.DataFrame(data=reporting_times).describe())
    # fig, ax = plt.subplots()
    # ax.boxplot(pd.DataFrame(data=reporting_times).delta_t, notch=True)
    # st.pyplot(fig)

    st.header('Approving Time')
    st.write(pd.DataFrame(data=approving_times))
    st.write(pd.DataFrame(data=approving_times).describe())
    # fig, ax = plt.subplots()
    # ax.boxplot(pd.DataFrame(data=approving_times).delta_t, notch=True)
    # st.pyplot(fig)

    st.header('TAT Time')
    st.write(pd.DataFrame(data=tat_times))
    st.write(pd.DataFrame(data=tat_times).describe())

    fig, ax = plt.subplots(nrows=1, ncols=2)
    ax[1].boxplot(pd.DataFrame(data=tat_times).delta_t, notch=True)
    st.pyplot(fig)
