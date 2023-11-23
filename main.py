import uuid
import random
import plotly.figure_factory as ff

import simpy
import streamlit as st

specimens_processing_times = []


def generate_random_labno(number=10):
    """Generate random lab numbers."""
    return [str(uuid.uuid4()) for i in range(number)]


def specimens(env, staff, labno, transport_time):
    """Check and evaluate an order and specimens.
    """
    start_t = env.now
    print(start_t)
    ln = labno[:8]
    yield env.timeout(transport_time)
    # st.write(f'{ln} arrived at {start_t}')
    with staff.request() as req:
        # st.write(f'{ln} waiting for the staff at {env.now}..')
        yield req
        # st.write(f'staff is available.')
        # st.write(f'Start scanning specimens {ln} at {env.now}..')
        yield env.timeout(random.randrange(5,10))
        finish_t = env.now
        specimens_processing_times.append(finish_t)
        # st.write(f'{ln} Finished scanning at {finish_t}')


st.title('MTForce: Medical Lab Workforce Simulation')

num_staff = st.number_input('Enter number of staff:', value=0)

if num_staff > 0:
    env = simpy.Environment()

    staff_resource = simpy.Resource(env, capacity=num_staff)

    wards = {
        'ER': 0,
        'IPD': 0,
        'OPD': 0
    }

    for n, labno in enumerate(generate_random_labno(20), start=1):
        ward = random.choice(list(wards.keys()))
        current_time = wards[ward]
        if current_time == 0:
            current_time = random.randrange(0, 9)
            arriving_time = current_time
        else:
            arriving_time = current_time * random.randrange(1, 3)
        wards[ward] = arriving_time
        env.process(specimens(env, staff_resource, labno, arriving_time))

    env.run()

    st.scatter_chart(specimens_processing_times)
    st.write(specimens_processing_times)
