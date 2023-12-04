"""
Code for clustering of univariate time-series data. See the documentation for all the details.
"""
import shutil
from functions import *

NUMBER_OF_SIGMAS = 2.0
OUTPUT_FILE = 'states_output.txt'
SHOW_PLOT = False

def all_the_input_stuff():
    """
    Reads input parameters and raw data from specified files and directories,
    processes the raw data, and creates output files.

    Returns:
    - m_raw: Processed raw data after removing initial frames based on 'tau_delay'.
    - par: Object containing input parameters.

    Notes:
    - Ensure 'input_parameters.txt' exists and contains necessary parameters.
    - 'OUTPUT_FILE' constant specifies the output file.
    - 'tau_delay' parameter from 'input_parameters.txt' determines frames removal.
    - Creates 'output_figures' directory for storing output files.
    """

    # Read input parameters from files.
    data_directory = read_input_data()
    par = Parameters('input_parameters.txt')
    par.print_to_screen()

    # Read raw data from the specified directory/files.
    if isinstance(data_directory, str):
        # if type(data_directory) == str:
        m_raw = read_data(data_directory)
    else:
        print('\tERROR: data_directory.txt is missing or wrongly formatted. ')

    # Remove initial frames based on 'tau_delay'.
    m_raw = m_raw[:, par.t_delay:]

    ### Create files for output
    with open(OUTPUT_FILE, 'w', encoding="utf-8") as file:
        print('#', file=file)
    figures_folder = 'output_figures'
    if not os.path.exists(figures_folder):
        os.makedirs(figures_folder)
    for filename in os.listdir(figures_folder):
        file_path = os.path.join(figures_folder, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as ex_msg:
            print(f'Failed to delete {file_path}. Reason: {ex_msg}')

    return m_raw, par

def preparing_the_data(m_raw: np.ndarray, par: Parameters):
    """
    Processes raw data for analysis.

    Args:
    - m_raw (np.ndarray): Raw input data.
    - par (Parameters): Object containing parameters for data processing.

    Returns:
    - m (np.ndarray): Processed data after filtering and normalization.
    - sig_range (list): List containing [min, max] values of the processed data.

    Notes:
    - Requires 'tau_w', 't_smooth', 't_conv', 't_units' parameters in the 'par' object.
    - Utilizes moving average filtering on the raw data.
    - Calculates statistics like maximum and minimum values of the processed data.
    - Prints informative messages about trajectory details.
    - Returns processed data and its signal range.
    """

    tau_window, t_smooth, t_conv, t_units = par.tau_w, par.t_smooth, par.t_conv, par.t_units

    # Apply filtering on the data
    m_clean = moving_average(m_raw, t_smooth)

    sig_max = np.max(m_clean)
    sig_min = np.min(m_clean)
    ###################################################################
    ### Normalize the data to the range [0, 1]. Usually not needed. ###
    # m_clean = (m_clean - sig_min)/(sig_max - sig_min)
    # sig_max = np.max(m_clean)
    # sig_min = np.min(m_clean)
    ###################################################################

    # Get the number of particles and total frames in the trajectory.
    tot_part = m_clean.shape[0]
    tot_time = m_clean.shape[1]

    # Calculate the number of windows for the analysis.
    num_windows = int(tot_time / tau_window)

    # Print informative messages about trajectory details.
    print('\tTrajectory has ' + str(tot_part) + ' particles. ')
    print('\tTrajectory of length ' + str(tot_time) +
        ' frames (' + str(tot_time*t_conv), t_units + ')')
    print('\tUsing ' + str(num_windows) + ' windows of length ' + str(tau_window) +
        ' frames (' + str(tau_window*t_conv), t_units + ')')

    return m_clean, [sig_min, sig_max]

def plot_input_data(m_clean: np.ndarray, par: Parameters, filename: str):
    """
    Plots input data for visualization.

    Args:
    - m_clean (np.ndarray): Processed data for plotting.
    - par (Parameters): Object containing parameters for plotting.
    - filename (str): Name of the output plot file.

    Notes:
    - Requires 'tau_w', 'tau_delay', 't_conv', 't_units', 'bins' parameters in the 'par' object.
    - Plots histogram counts and bins of the flattened data.
    - Generates a plot with two subplots (signal trajectories and histogram).
    - Saves the plot as a PNG file in the 'output_figures' directory.
    - Allows toggling plot display based on 'SHOW_PLOT' constant.
    """

    # Flatten the m_clean matrix and compute histogram counts and bins
    flat_m = m_clean.flatten()
    bins = par.bins
    counts, bins = np.histogram(flat_m, bins=bins, density=True)
    counts *= flat_m.size

    # Create a plot with two subplots (side-by-side)
    fig, ax = plt.subplots(1, 2, sharey=True,
        gridspec_kw={'width_ratios': [3, 1]},figsize=(9, 4.8))

    # Plot histogram in the second subplot (right side)
    ax[1].stairs(counts, bins, fill=True, orientation='horizontal')

    # Plot the individual trajectories in the first subplot (left side)
    time = par.print_time(m_clean.shape[1])
    step = 10 if m_clean.size > 1000000 else 1
    for mol in m_clean[::step]:
        ax[0].plot(time, mol, c='xkcd:black', lw=0.1, alpha=0.5, rasterized=True)

    # Set labels and titles for the plots
    ax[0].set_ylabel('Signal')
    ax[0].set_xlabel(r'Simulation time $t$ ' + par.t_units)
    ax[1].set_xticklabels([])

    if SHOW_PLOT:
        plt.show()
    fig.savefig('output_figures/' + filename + '.png', dpi=600)
    plt.close(fig)

def perform_gaussian_fit(
        id0: int, id1: int, max_ind: int, bins: np.ndarray,
        counts: np.ndarray, n_data: int, gap: int, interval_type: str
    ):
    """
    Perform Gaussian fit on given data within the specified range and parameters.

    Parameters:
    - id0 (int): Index representing the lower limit for data selection.
    - id1 (int): Index representing the upper limit for data selection.
    - bins (np.ndarray): Array containing bin values.
    - counts (np.ndarray): Array containing counts corresponding to bins.
    - n_data (int): Number of data points.
    - gap (int): Gap value for the fit.
    - interval_type (str): Type of interval.

    Returns:
    - tuple: A tuple containing:
        - bool: True if the fit is successful, False otherwise.
        - int: Goodness value calculated based on fit quality.
        - array or None: Parameters of the Gaussian fit if successful, None otherwise.

    The function performs a Gaussian fit on the specified data within the provided range.
    It assesses the goodness of the fit based on various criteria and returns the result.
    """
    goodness = 5
    selected_bins = bins[id0:id1]
    selected_counts = counts[id0:id1]
    mu0 = bins[max_ind]
    sigma0 = (bins[id0] - bins[id1])/6
    area0 = counts[max_ind]*np.sqrt(np.pi)*sigma0
    try:
        popt, pcov = scipy.optimize.curve_fit(gaussian, selected_bins, selected_counts,
            p0=[mu0, sigma0, area0])
        if popt[1] < 0:
            popt[1] = -popt[1]
            popt[2] = -popt[2]
        gauss_max = popt[2]*np.sqrt(np.pi)*popt[1]
        if gauss_max < area0/2:
            goodness -= 1
        popt[2] *= n_data
        if popt[0] < selected_bins[0] or popt[0] > selected_bins[-1]:
            goodness -= 1
        if popt[1] > selected_bins[-1] - selected_bins[0]:
            goodness -= 1
        perr = np.sqrt(np.diag(pcov))
        for j, par_err in enumerate(perr):
            if par_err/popt[j] > 0.5:
                goodness -= 1
        if id1 - id0 <= gap:
            goodness -= 1
        return True, goodness, popt
    except RuntimeError:
        print('\t' + interval_type + ' fit: Runtime error. ')
        return False, goodness, None
    except TypeError:
        print('\t' + interval_type + ' fit: TypeError.')
        return False, goodness, None
    except ValueError:
        print('\t' + interval_type + ' fit: ValueError.')
        return False, goodness, None

def gauss_fit_max(m_clean: np.ndarray, par: Parameters, filename: str):
    """
    Performs Gaussian fitting on input data.

    Args:
    - m_clean (np.ndarray): Input data for Gaussian fitting.
    - par (Parameters): Object containing parameters for fitting.
    - filename (str): Name of the output plot file.

    Returns:
    - state (State): Object containing Gaussian fit parameters (mu, sigma, area).

    Notes:
    - Requires 'bins' parameter in the 'par' object.
    - Performs Gaussian fitting on flattened input data.
    - Tries to find the maximum and fit Gaussians based on surrounding minima.
    - Chooses the best fit among the options or returns None if fitting fails.
    - Prints fit details and goodness of fit to an output file.
    - Generates a plot showing the distribution and the fitted Gaussian.
    - Allows toggling plot display based on 'SHOW_PLOT' constant.
    """

    print('* Gaussian fit...')
    flat_m = m_clean.flatten()

    ### 1. Histogram ###
    counts, bins = np.histogram(flat_m, bins=par.bins, density=True)
    gap = 1
    if bins.size > 50:
        gap = 3

    ### 2. Smoothing with tau = 3 ###
    counts = moving_average(counts, gap)
    bins = moving_average(bins, gap)

    ### 3. Find the maximum ###
    max_val = counts.max()
    max_ind = counts.argmax()

    ### 4. Find the minima surrounding it ###
    min_id0 = np.max([max_ind - gap, 0])
    min_id1 = np.min([max_ind + gap, counts.size - 1])
    while min_id0 > 0 and counts[min_id0] > counts[min_id0 - 1]:
        min_id0 -= 1
    while min_id1 < counts.size - 1 and counts[min_id1] > counts[min_id1 + 1]:
        min_id1 += 1

    ### 5. Try the fit between the minima and check its goodness ###
    flag_min, goodness_min, popt_min = perform_gaussian_fit(min_id0,
        min_id1, max_ind, bins, counts, flat_m.size, gap, 'Min')

    ### 6. Find the inrterval of half height ###
    half_id0 = np.max([max_ind - gap, 0])
    half_id1 = np.min([max_ind + gap, counts.size - 1])
    while half_id0 > 0 and counts[half_id0] > max_val/2:
        half_id0 -= 1
    while half_id1 < counts.size - 1 and counts[half_id1] > max_val/2:
        half_id1 += 1

    ### 7. Try the fit between the minima and check its goodness ###
    flag_half, goodness_half, popt_half = perform_gaussian_fit(half_id0,
        half_id1, max_ind, bins, counts, flat_m.size, gap, 'Half')

    ### 8. Choose the best fit ###
    goodness = goodness_min
    if flag_min == 1 and flag_half == 0:
        popt = popt_min
    elif flag_min == 0 and flag_half == 1:
        popt = popt_half
        goodness = goodness_half
    elif flag_min*flag_half == 1:
        if goodness_min >= goodness_half:
            popt = popt_min
        else:
            popt = popt_half
            goodness = goodness_half
    else:
        print('\tWARNING: this fit is not converging.')
        return None

    state = State(popt[0], popt[1], popt[2])
    state.build_boundaries(NUMBER_OF_SIGMAS)

    with open(OUTPUT_FILE, 'a', encoding="utf-8") as file:
        print('\n', file=file)
        print(f'\tmu = {state.mean:.4f}, sigma = {state.sigma:.4f}, area = {state.area:.4f}')
        print(f'\tmu = {state.mean:.4f}, sigma = {state.sigma:.4f}, area = {state.area:.4f}',
            file=file)
        print('\tFit goodness = ' + str(goodness), file=file)

    ### Plot the distribution and the fitted gaussians
    y_spread = np.max(m_clean) - np.min(m_clean)
    y_lim = [np.min(m_clean) - 0.025*y_spread, np.max(m_clean) + 0.025*y_spread]
    fig, ax = plt.subplots()
    plot_histo(ax, counts, bins)
    ax.set_xlim(y_lim)
    tmp_popt = [state.mean, state.sigma, state.area/flat_m.size]
    ax.plot(np.linspace(bins[0], bins[-1], 1000),
        gaussian(np.linspace(bins[0], bins[-1], 1000), *tmp_popt))

    if SHOW_PLOT:
        plt.show()
    fig.savefig(filename + '.png', dpi=600)
    plt.close(fig)

    return state

def find_stable_trj(
        m_clean: np.ndarray, tau_window: int, state: State,
        all_the_labels: np.ndarray, offset: int
    ):
    """
    Identifies stable windows in a trajectory based on criteria.

    Args:
    - m_clean (np.ndarray): Input trajectory data.
    - tau_window (int): Size of the window for analysis.
    - state (State): Object containing stable state parameters.
    - all_the_labels (np.ndarray): Labels indicating window classifications.
    - offset (int): Offset value for classifying stable windows.

    Returns:
    - m2_array (np.ndarray): Array of non-stable windows.
    - fw (float): Fraction of windows classified as stable.
    - one_last_state (bool): Indicates if there's one last state remaining.

    Notes:
    - Computes stable windows using criteria based on given state thresholds.
    - Updates the window labels to indicate stable windows with an offset.
    - Calculates the fraction of stable windows found and prints the value.
    - Returns the array of non-stable windows and related information.
    """

    print('* Finding stable windows...')

    # Calculate the number of windows in the trajectory
    number_of_windows = all_the_labels.shape[1]

    mask_unclassified = all_the_labels < 0.5
    m_reshaped = m_clean[:, :number_of_windows*tau_window].reshape(m_clean.shape[0],
        number_of_windows, tau_window)
    mask_inf = np.min(m_reshaped, axis=2) >= state.th_inf[0]
    mask_sup = np.max(m_reshaped, axis=2) <= state.th_sup[0]
    mask = mask_unclassified & mask_inf & mask_sup

    all_the_labels[mask] = offset + 1
    counter = np.sum(mask)

    # Initialize an empty list to store non-stable windows
    remaning_data = []
    mask_remaining = mask_unclassified & ~mask
    for i, window in np.argwhere(mask_remaining):
        r_w = m_clean[i, window*tau_window:(window + 1)*tau_window]
        remaning_data.append(r_w)

    # Calculate the fraction of stable windows found
    window_fraction = counter/(all_the_labels.size)

    # Print the fraction of stable windows
    with open(OUTPUT_FILE, 'a', encoding="utf-8") as file:
        print(f'\tFraction of windows in state {offset + 1} = {window_fraction:.3}')
        print(f'\tFraction of windows in state {offset + 1} = {window_fraction:.3}', file=file)

    # Convert the list of non-stable windows to a NumPy array
    m2_array = np.array(remaning_data)
    one_last_state = True
    if len(m2_array) == 0:
        one_last_state = False

    # Return the array of non-stable windows, the fraction of stable windows,
    # and the updated list_of_states
    return m2_array, window_fraction, one_last_state

def iterative_search(m_clean: np.ndarray, par: Parameters, name: str):
    """
    Performs an iterative search for stable states in a trajectory.

    Args:
    - m (np.ndarray): Input trajectory data.
    - par (Parameters): Object containing parameters for the search.
    - name (str): Name for identifying output figures.

    Returns:
    - atl (np.ndarray): Updated labels for each window.
    - lis (list): List of identified states.
    - one_last_state (bool): Indicates if there's one last state remaining.

    Notes:
    - Divides the trajectory into windows and iteratively identifies stable states.
    - Uses Gaussian fitting and stability criteria to determine stable windows.
    - Updates labels for each window based on identified stable states.
    - Returns the updated labels, list of identified states, and a flag for one last state.
    """

    # Initialize an array to store labels for each window.
    num_windows = int(m_clean.shape[1] / par.tau_w)
    all_the_labels = np.zeros((m_clean.shape[0], num_windows))

    states_list = []
    m_copy = m_clean
    iteration_id = 1
    states_counter = 0
    one_last_state = False
    while True:
        ### Locate and fit maximum in the signal distribution
        state = gauss_fit_max(m_copy, par, 'output_figures/' + name + 'Fig1_' + str(iteration_id))
        if state is None:
            print('Iterations interrupted because unable to fit a Gaussian over the histogram. ')
            break

        ### Find the windows in which the trajectories are stable in the maximum
        m_next, counter, one_last_state = find_stable_trj(m_clean, par.tau_w, state,
            all_the_labels, states_counter)
        state.perc = counter

        states_list.append(state)
        states_counter += 1
        iteration_id += 1
        ### Exit the loop if no new stable windows are found
        if counter <= 0.0:
            print('Iterations interrupted because no data point has been assigned to last state. ')
            break
        m_copy = m_next

    atl, lis = relabel_states(all_the_labels, states_list)
    return atl, lis, one_last_state

def plot_cumulative_figure(m_clean: np.ndarray, par: Parameters,
    list_of_states: list[State], filename: str):
    """
    Generates a cumulative figure with signal trajectories and state Gaussian distributions.

    Args:
    - m_clean (np.ndarray): Input trajectory data.
    - par (Parameters): Object containing parameters for plotting.
    - list_of_states (list[State]): List of identified states.
    - filename (str): Name for the output figure file.

    Notes:
    - Plots signal trajectories and Gaussian distributions of identified states.
    - Visualizes state thresholds and their corresponding signal ranges.
    - Saves the figure as a PNG file in the 'output_figures' directory.
    - Allows toggling plot display based on 'SHOW_PLOT' constant.
    """

    print('* Printing cumulative figure...')
    t_units, bins = par.t_units, par.bins
    n_states = len(list_of_states)

    # Compute histogram of flattened m_clean
    flat_m = m_clean.flatten()
    counts, bins = np.histogram(flat_m, bins=bins, density=True)
    counts *= flat_m.size

    # Create a 1x2 subplots with shared y-axis
    fig, ax = plt.subplots(1, 2, sharey=True, gridspec_kw={'width_ratios': [3, 1]},
        figsize=(9, 4.8))

    # Plot the histogram on the right subplot (ax[1])
    ax[1].stairs(counts, bins, fill=True, orientation='horizontal', alpha=0.5)

    # Create a color palette for plotting states
    palette = []
    cmap = plt.get_cmap('viridis', n_states + 1)
    for i in range(1, cmap.N):
        rgba = cmap(i)
        palette.append(rgb2hex(rgba))

    # Define time and y-axis limits for the left subplot (ax[0])
    y_spread = np.max(m_clean) - np.min(m_clean)
    y_lim = [np.min(m_clean) - 0.025*y_spread, np.max(m_clean) + 0.025*y_spread]
    time = par.print_time(m_clean.shape[1])

    # Plot the individual trajectories on the left subplot (ax[0])
    step = 10 if m_clean.size > 1000000 else 1
    for mol in m_clean[::step]:
        ax[0].plot(time, mol, c='xkcd:black', ms=0.1, lw=0.1, alpha=0.5, rasterized=True)

    # Plot the Gaussian distributions of states on the right subplot (ax[1])
    for state_id, state in enumerate(list_of_states):
        popt = [state.mean, state.sigma, state.area]
        ax[1].plot(gaussian(np.linspace(bins[0], bins[-1], 1000), *popt),
            np.linspace(bins[0], bins[-1], 1000), color=palette[state_id])

    # Plot the horizontal lines and shaded regions to mark states' thresholds
    style_color_map = {
        0: ('--', 'xkcd:black'),
        1: ('--', 'xkcd:blue'),
        2: ('--', 'xkcd:red'),
    }

    time2 = np.linspace(time[0] - 0.05*(time[-1] - time[0]),
        time[-1] + 0.05*(time[-1] - time[0]), 100)
    for state_id, state in enumerate(list_of_states):
        linestyle, color = style_color_map.get(state.th_inf[1], ('-', 'xkcd:black'))
        ax[1].hlines(state.th_inf[0], xmin=0.0, xmax=np.amax(counts),
            linestyle=linestyle, color=color)
        ax[0].fill_between(time2, state.th_inf[0], state.th_sup[0],
            color=palette[state_id], alpha=0.25)
    ax[1].hlines(list_of_states[-1].th_sup[0], xmin=0.0, xmax=np.amax(counts),
        linestyle=linestyle, color='black')

    # Set plot titles and axis labels
    ax[0].set_ylabel('Signal')
    ax[0].set_xlabel(r'Time $t$ ' + t_units)
    ax[0].set_xlim([time2[0], time2[-1]])
    ax[0].set_ylim(y_lim)
    ax[1].set_xticklabels([])

    if SHOW_PLOT:
        plt.show()
    fig.savefig('output_figures/' + filename + '.png', dpi=600)
    plt.close(fig)

def plot_one_trajectory(m_clean: np.ndarray, par: Parameters,
    all_the_labels: np.ndarray, filename: str):
    """
    Plots a single trajectory of an example particle with labeled data points.

    Args:
    - m (np.ndarray): Input trajectory data.
    - par (Parameters): Object containing parameters for plotting.
    - all_the_labels (np.ndarray): Labels indicating data points' classifications.
    - filename (str): Name for the output figure file.

    Notes:
    - Plots a single trajectory with labeled data points based on classifications.
    - Uses a colormap to differentiate and visualize different data point labels.
    - Saves the figure as a PNG file in the 'output_figures' directory.
    - Allows toggling plot display based on 'SHOW_PLOT' constant.
    """

    example_id = par.example_id
    # Get the signal of the example particle
    signal = m_clean[example_id][:all_the_labels.shape[1]]

    # Create time values for the x-axis
    time = par.print_time(all_the_labels.shape[1])

    # Create a figure and axes for the plot
    fig, ax = plt.subplots()

    # Create a colormap to map colors to the labels of the example particle
    cmap = plt.get_cmap('viridis',
        np.max(np.unique(all_the_labels)) - np.min(np.unique(all_the_labels)) + 1)
    color = all_the_labels[example_id]
    ax.plot(time, signal, c='black', lw=0.1)

    # Plot the signal as a line and scatter plot with colors based on the labels
    ax.scatter(time, signal, c=color, cmap=cmap,
        vmin=np.min(np.unique(all_the_labels)), vmax=np.max(np.unique(all_the_labels)), s=1.0)

    # Add title and labels to the axes
    fig.suptitle('Example particle: ID = ' + str(example_id))
    ax.set_xlabel('Time ' + par.t_units)
    ax.set_ylabel('Normalized signal')

    if SHOW_PLOT:
        plt.show()
    fig.savefig('output_figures/' + filename + '.png', dpi=600)
    plt.close(fig)

def timeseries_analysis(m_raw: np.ndarray, par: Parameters, tau_w: int, t_smooth: int):
    """
    Performs an analysis pipeline on time series data.

    Args:
    - m_raw (np.ndarray): Raw input time series data.
    - par (Parameters): Object containing parameters for analysis.
    - tau_w (int): the time window for the analysis
    - t_smooth (int): the width of the moving average for the analysis

    Returns:
    - num_states (int): Number of identified states.
    - fraction_0 (float): Fraction of unclassified data points.

    Notes:
    - Prepares the data, performs an iterative search for states, and sets final states.
    - Analyzes the time series data based on specified parameters in the 'par' object.
    - Handles memory cleanup after processing to prevent accumulation.
    - Returns the number of identified states and the fraction of unclassified data points.
    """

    print('* New analysis: ', tau_w, t_smooth)
    name = str(t_smooth) + '_' + str(tau_w) + '_'

    tmp_par = par.create_copy()
    tmp_par.tau_w = tau_w
    tmp_par.t_smooth = t_smooth

    m_clean, m_range = preparing_the_data(m_raw, tmp_par)
    plot_input_data(m_clean, tmp_par, name + 'Fig0')

    all_the_labels, list_of_states, one_last_state = iterative_search(m_clean, tmp_par, name)

    if len(list_of_states) == 0:
        print('* No possible classification was found. ')
        # We need to free the memory otherwise it accumulates
        del m_raw
        del m_clean
        del all_the_labels
        return 1, 1.0

    list_of_states, all_the_labels = set_final_states(list_of_states, all_the_labels, m_range)

    # We need to free the memory otherwise it accumulates
    del m_raw
    del m_clean
    del all_the_labels

    fraction_0 = 1 - np.sum([ state.perc for state in list_of_states ])
    if one_last_state:
        print('Number of states identified:', len(list_of_states) + 1,
            '[' + str(fraction_0) + ']\n')
        return len(list_of_states) + 1, fraction_0

    print('Number of states identified:', len(list_of_states), '[' + str(fraction_0) + ']\n')
    return len(list_of_states), fraction_0

def compute_cluster_mean_seq(m_clean: np.ndarray, all_the_labels: np.ndarray, tau_window: int):
    """
    Computes and plots the average time sequence inside each identified environment.

    Args:
    - m_clean (np.ndarray): Input data containing signal trajectories.
    - all_the_labels (np.ndarray): Labels indicating data points' cluster assignments.
    - tau_window (int): Size of the time window.

    Notes:
    - Computes cluster means and standard deviations for each identified cluster.
    - Plots the average time sequence and standard deviation for each cluster.
    - Saves the figure as a PNG file in the 'output_figures' directory.
    - Allows toggling plot display based on 'SHOW_PLOT' constant.
    """

    # Initialize lists to store cluster means and standard deviations
    center_list = []
    std_list = []

    # Loop through unique labels (clusters)
    for ref_label in np.unique(all_the_labels):
        tmp = []
        # Iterate through molecules and their labels
        for i, mol in enumerate(all_the_labels):
            for window, label in enumerate(mol):
                 # Define time interval
                time_0 = window*tau_window
                time_1 = (window + 1)*tau_window
                # If the label matches the current cluster, append the corresponding data to tmp
                if label == ref_label:
                    tmp.append(m_clean[i][time_0:time_1])

        # Calculate mean and standard deviation for the current cluster
        center_list.append(np.mean(tmp, axis=0))
        std_list.append(np.std(tmp, axis=0))

    # Create a color palette
    palette = []
    cmap = plt.get_cmap('viridis', np.unique(all_the_labels).size)
    palette.append(rgb2hex(cmap(0)))
    for i in range(1, cmap.N):
        rgba = cmap(i)
        palette.append(rgb2hex(rgba))

    # Plot
    fig, ax = plt.subplots()
    time_seq = range(tau_window)
    for center_id, center in enumerate(center_list):
        err_inf = center - std_list[center_id]
        err_sup = center + std_list[center_id]
        ax.fill_between(time_seq, err_inf, err_sup, alpha=0.25, color=palette[center_id])
        ax.plot(time_seq, center, label='ENV'+str(center_id), marker='o', c=palette[center_id])
    fig.suptitle('Average time sequence inside each environments')
    ax.set_xlabel(r'Time $t$ [frames]')
    ax.set_ylabel(r'Signal')
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.legend()

    if SHOW_PLOT:
        plt.show()
    fig.savefig('output_figures/Fig4.png', dpi=600)

def full_output_analysis(m_raw: np.ndarray, par: Parameters):
    """
    Conducts a comprehensive analysis pipeline on a dataset,
    generating multiple figures and outputs.

    Args:
    - m_raw (np.ndarray): Raw input data.
    - par (Parameters): Object containing parameters for analysis.

    Notes:
    - Prepares the data, conducts iterative search for states, and sets final states.
    - Computes cluster mean sequences, assigns single frames, and generates various plots.
    - Prints molecular labels and colored trajectories based on analysis results.
    - Allows toggling plot display based on 'SHOW_PLOT' constant.
    """

    tau_w = par.tau_w
    m_clean, m_range = preparing_the_data(m_raw, par)
    plot_input_data(m_clean, par, 'Fig0')

    all_the_labels, list_of_states, _ = iterative_search(m_clean, par, '')
    if len(list_of_states) == 0:
        print('* No possible classification was found. ')
        return
    list_of_states, all_the_labels = set_final_states(list_of_states, all_the_labels, m_range)

    compute_cluster_mean_seq(m_clean, all_the_labels, tau_w)

    all_the_labels = assign_single_frames(all_the_labels, tau_w)

    plot_cumulative_figure(m_clean, par, list_of_states, 'Fig2')
    plot_one_trajectory(m_clean, par, all_the_labels, 'Fig3')
    # sankey(all_the_labels, [0, 100, 200, 300], par, 'Fig5', SHOW_PLOT)
    plot_state_populations(all_the_labels, par, 'Fig5', SHOW_PLOT)

    print_mol_labels_fbf_xyz(all_the_labels)
    print_colored_trj_from_xyz('trajectory.xyz', all_the_labels, par)

def time_resolution_analysis(m_raw: np.ndarray, par: Parameters, perform_anew: bool):
    """
    Performs Temporal Resolution Analysis (TRA) to explore parameter space and analyze the dataset.

    Args:
    - m_raw (np.ndarray): Raw input data.
    - par (Parameters): Object containing parameters for analysis.
    - perform_anew (bool): Flag to indicate whether to perform analysis anew
        or load previous results.

    Notes:
    - Conducts TRA for different combinations of parameters.
    - Analyzes the dataset with varying 'tau_window' and 't_smooth'.
    - Saves results to text files and plots t.r.a. figures based on analysis outcomes.
    - Allows toggling plot display based on 'SHOW_PLOT' constant.
    """

    tau_window_list, t_smooth_list = param_grid(par, m_raw.shape[1])

    if perform_anew:
        ### If the analysis hat to be performed anew ###
        number_of_states = []
        fraction_0 = []
        for tau_w in tau_window_list:
            tmp = [tau_w]
            tmp1 = [tau_w]
            for t_s in t_smooth_list:
                n_s, f_0 = timeseries_analysis(m_raw, par, tau_w, t_s)
                tmp.append(n_s)
                tmp1.append(f_0)
            number_of_states.append(tmp)
            fraction_0.append(tmp1)
        number_of_states_arr = np.array(number_of_states)
        fraction_0_arr = np.array(fraction_0)

        np.savetxt('number_of_states.txt', number_of_states, fmt='%i',
            delimiter='\t', header='tau_window\n number_of_states for different t_smooth')
        np.savetxt('fraction_0.txt', fraction_0, delimiter=' ',
            header='tau_window\n fraction in ENV0 for different t_smooth')
    else:
        ### Otherwise, just do this ###
        number_of_states_arr = np.loadtxt('number_of_states.txt')
        fraction_0_arr = np.loadtxt('fraction_0.txt')

    plot_tra_figure(number_of_states_arr, fraction_0_arr, par, SHOW_PLOT)

def main():
    """
    all_the_input_stuff() reads the data and the parameters
    time_resolution_analysis() explore the parameter (tau_window, t_smooth) space.
        Use 'False' to skip it.
    full_output_analysis() performs a detailed analysis with the chosen parameters.
    """
    m_raw, par = all_the_input_stuff()
    time_resolution_analysis(m_raw, par, True)
    full_output_analysis(m_raw, par)

if __name__ == "__main__":
    main()
