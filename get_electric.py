import numpy as np
from scipy.interpolate import interp1d
from numpy import trapz  # Corrected import

def get_electric(lam, T):
    """
    Calculates the short-circuit current density (Jsc), open-circuit voltage (Voc),
    current (I), voltage (V), and power (P) for a photovoltaic (PV) cell.

    Parameters:
    - lam: Wavelengths (in nm).
    - T: Transmittance values.

    Returns:
    - IV: A dictionary containing the calculated electrical properties.
    """

    # Ensure lam is a column vector
    if lam.ndim == 1:
        lam = lam[:, np.newaxis]

    # Constants
    nm = 1e-9
    ec = 1.60217663e-19  # Electron charge (Coulombs)
    h = 6.62607015e-34  # Planck's constant (Joule seconds)
    c = 3e8  # Speed of light in vacuum (m/s)
    k = 1.380649e-23  # Boltzmann constant (Joule per Kelvin)
    T_room = 300  # Room temperature (Kelvin)
    n = 1
    I0 = 55e-12  # Dark saturation current (A)
    cjsc = ec / (h * c)
    cvoc = n * k * T_room / ec

    # Load AM1.5 and IQE data
    AM15_data = np.loadtxt("AM15.csv", delimiter=',', skiprows=1)  # Assuming it's a CSV file
    IQE_data = np.loadtxt("IQE.csv", delimiter=',', skiprows=1)    # Assuming it's a CSV file

    # Interpolate the AM1.5 spectrum and IQE data to match the wavelength range
    AM15_lam = interp1d(AM15_data[:, 0], AM15_data[:, 1], kind='linear', fill_value="extrapolate")(lam.flatten())
    IQE_lam = interp1d(IQE_data[:, 0], IQE_data[:, 1], kind='linear', fill_value="extrapolate")(lam.flatten())

    # Calculate Jsc (Short-circuit current density)
    jsc = trapz(lam.flatten() * nm, cjsc * AM15_lam * IQE_lam * T.flatten() * lam.flatten() / 10) * 1.046

    # Calculate Voc (Open-circuit voltage)
    Voc = cvoc * np.log(jsc / I0)

    # Generate IV curve
    V = np.linspace(0, Voc, 1000)
    I = jsc - I0 * (np.exp(V / cvoc) - 1)
    P = I * V

    # Find maximum power point
    Pmax = np.max(P)
    Imax = np.max(I)

    # Store results in a dictionary
    IV = {
        "jsc": jsc,
        "Voc": Voc,
        "V": V,
        "I": I,
        "P": P,
        "Pmax": Pmax,
        "Imax": Imax
    }

    return IV
