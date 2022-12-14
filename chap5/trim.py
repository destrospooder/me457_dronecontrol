"""
compute_trim 
    - Chapter 5 assignment for Beard & McLain, PUP, 2012
    - Update history:  
        12/29/2018 - RWB
"""
import sys
sys.path.append('..')
import numpy as np
from scipy.optimize import minimize
from tools.rotations import Euler2Quaternion
from message_types.msg_delta import MsgDelta

def compute_trim(mav, Va, gamma):
    # define initial state and input
    e = Euler2Quaternion(0., gamma, 0.)
    state0 = np.array([[mav._state.item(0)], #pn
                       [mav._state.item(1)], #pe
                       [mav._state.item(2)], #pd
                       [Va],    # u0
                       [0.0],    # v0
                       [0.0],    # w0
                       [e[0]],    # e0
                       [e[1]],    # e1
                       [e[2]],    # e2
                       [e[3]],    # e3
                       [0.0],    # p0
                       [0.0],    # q0
                       [0.0]])   # r0
    delta0 = MsgDelta()
    x0 = np.concatenate((state0, delta0.to_array()), axis=0)
    # define equality constraints
    cons = ({'type': 'eq',
             'fun': lambda x: np.array([
                                x[3]**2 + x[4]**2 + x[5]**2 - Va**2,  # magnitude of velocity vector is Va
                                x[4],  # v=0, force side velocity to be zero
                                x[6]**2 + x[7]**2 + x[8]**2 + x[9]**2 - 1.,  # force quaternion to be unit length
                                x[7],  # e1=0  - forcing e1=e3=0 ensures zero roll and zero yaw in trim
                                x[9],  # e3=0
                                x[10],  # p=0  - angular rates should all be zero
                                x[11],  # q=0
                                x[12],  # r=0
                                ]),
             'jac': lambda x: np.array([
                                [0., 0., 0., 2*x[3], 2*x[4], 2*x[5], 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.],
                                [0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.],
                                [0., 0., 0., 0., 0., 0., 2*x[6], 2*x[7], 2*x[8], 2*x[9], 0., 0., 0., 0., 0., 0., 0.],
                                [0., 0., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 0., 0., 0., 0.],
                                [0., 0., 0., 0., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 0., 0.],
                                [0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 0.],
                                [0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0.],
                                [0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0.],
                                ])
             })
    # solve the minimization problem to find the trim states and inputs

    res = minimize(trim_objective_fun, x0, method='SLSQP', args=(mav, Va, gamma),
                   constraints=cons, options={'ftol': 1e-10, 'disp': True})
    # extract trim state and input and return
    trim_state = np.array([res.x[0:13]]).T
    trim_input = MsgDelta(elevator=res.x.item(13),
                          aileron=res.x.item(14),
                          rudder=res.x.item(15),
                          throttle=res.x.item(16))
    trim_input.print()
    print('trim_state=', trim_state.T)
    return trim_state, trim_input


def trim_objective_fun(x, mav, Va, gamma):
    # objective function to be minimized

    # BA - See Ch. 5, Slide 19 for trim objective fn
    state = x[0:13]
    delta = MsgDelta(elevator = x[13],
                     aileron = x[14],
                     rudder = x[15],
                     throttle = x[16])
    xd = np.array([[0, 0, -Va * np.sin(gamma), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]).T
    mav._state = state
    mav._update_velocity_data()
    fm = mav._forces_moments(delta)
    f = mav._derivatives(state, fm)
    e = xd - f
    J = np.linalg.norm(e[2:13]) ** 2
    return J
