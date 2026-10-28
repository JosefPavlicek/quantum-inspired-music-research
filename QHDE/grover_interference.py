"""Demonstration of Grover amplification: 2 qubits, target bit string 01.
NumPy only, no QPU consumption.
"""
import numpy as np

labels = ('00', '01', '10', '11')
state = np.ones(4, dtype=complex) / 2

def report(title, vector):
    print('\n' + title)
    for label, amp in zip(labels, vector):
        print(f'{label}: amplitude={amp.real:+.3f}, probability={abs(amp)**2:.3f}')

report('1. Uniform superposition', state)
state[1] *= -1  # Phase oracle recognizes target 01
report('2. Phase oracle: marked state has negative amplitude', state)
state = 2 * np.mean(state) - state  # Reflection about the mean
report('3. Diffusion: interference concentrates probability', state)
assert np.allclose(abs(state)**2, [0, 1, 0, 0])
