import random
import copy
from collections import deque
import math
import argparse
import os
import sys


# Objective function
def objective_function(bins, bin_capacity, expected_items_count=None):
    total_items = sum(len(bin) for bin in bins)
    if expected_items_count is not None and total_items != expected_items_count:
        return float('inf')

    for bin in bins:
        if sum(bin) > bin_capacity:
            return float('inf')

    # Premia za efektywne wykorzystanie pojemnikow
    space_wasted = sum(bin_capacity - sum(bin) for bin in bins)
    #(koszt - pojemniki) / 0.1
    return len(bins) + 0.1 * space_wasted

# Random Solution
def random_solution(items, bin_capacity):
    items = items.copy()
    random.shuffle(items)
    bins = []

    for item in items:
        if not bins:
            bins.append([item])
        else:
            last_bin = bins[-1]
            if sum(last_bin) + item <= bin_capacity:
                last_bin.append(item)
            else:
                bins.append([item])

    return bins

# Generowanie neighbours
def generate_neighbours(bins, bin_capacity):
    neighbours = []

    for from_bin_index, from_bin in enumerate(bins):
        for item_index, item in enumerate(from_bin):
            new_from_bin = from_bin[:item_index] + from_bin[item_index + 1:] #nowa wersja bez elementu

            for to_bin_index, to_bin in enumerate(bins):
                if to_bin_index == from_bin_index:
                    continue

                if sum(to_bin) + item <= bin_capacity:
                    new_bins = [b.copy() for b in bins]
                    new_bins[from_bin_index] = new_from_bin
                    new_bins[to_bin_index].append(item)
                    new_bins = [b for b in new_bins if b] #usuwanie pustych
                    neighbours.append(new_bins)

            # Dodanie nowego pojemnika
            new_bins = [b.copy() for b in bins]
            new_bins[from_bin_index] = new_from_bin
            new_bins.append([item])
            new_bins = [b for b in new_bins if b]
            neighbours.append(new_bins)

            if new_bins != bins:
                neighbours.append(new_bins) #zabezpieczenie przed zmianami bez celu

    return neighbours

# Algorytm pelnego przegladu
def generate_all_valid_bin_packings(items, bin_capacity):
    results = []

    def backtrack(remaining_items, current_bins):
        if not remaining_items:
            results.append(current_bins)
            return

        for i in range(len(current_bins)):
            bin_copy = current_bins[i][:]
            if sum(bin_copy) + remaining_items[0] <= bin_capacity:
                bin_copy.append(remaining_items[0])
                new_bins = current_bins[:i] + [bin_copy] + current_bins[i+1:]
                backtrack(remaining_items[1:], new_bins) #rekurencyjne wywolanie


        backtrack(remaining_items[1:], current_bins + [[remaining_items[0]]])

    backtrack(items, [])
    return results

def brute_force_optimal_bin_packing(items, bin_capacity):
    best_solution = None
    best_cost = float('inf')

    all_packings = generate_all_valid_bin_packings(items, bin_capacity)

    for packing in all_packings:
        cost = objective_function(packing, bin_capacity)
        if cost < best_cost:
            best_cost = cost
            best_solution = packing

    return best_solution, best_cost

# Hill Climbing best neighbour
def hill_climbing_bin_packing(items, bin_capacity, max_iterations):
    current_items = items.copy()

    # pierwsze rozwiązanie na bazie random_solution
    current_bins = random_solution(current_items, bin_capacity)
    current_cost = objective_function(current_bins, bin_capacity)

    for _ in range(max_iterations):
        # generowanie sąsiadów na podstawie pojemników
        neighbours = generate_neighbours(current_bins, bin_capacity)
        improved = False

        for neighbour_bins in neighbours:
            neighbour_cost = objective_function(neighbour_bins, bin_capacity)

            if neighbour_cost < current_cost:
                current_bins = neighbour_bins
                current_cost = neighbour_cost
                improved = True
                break  # pierwszy lepszy

        if not improved:
            break  # lokalne optimum – nic lepszego nie ma

    return current_bins, current_cost

# Hill Climb random
def stochastic_hill_climbing_bin_packing(items, bin_capacity, max_iterations):
    current_items = items.copy()

    current_bins = random_solution(current_items, bin_capacity)
    current_cost = objective_function(current_bins, bin_capacity)

    for _ in range(max_iterations):
        neighbours = generate_neighbours(current_bins, bin_capacity)
        if not neighbours:
            break

        # losowy sąsiad spośród całego otoczenia
        neighbour_bins = random.choice(neighbours)
        neighbour_cost = objective_function(neighbour_bins, bin_capacity)

        if neighbour_cost < current_cost:
            current_bins = neighbour_bins
            current_cost = neighbour_cost

    return current_bins, current_cost

# Algorytm tabu search
def tabu_search_bin_packing(items, bin_capacity, tabu_size=15, max_iterations=1000):

    # Tworzenie początkowego losowego rozwiązania
    current_bins = random_solution(items, bin_capacity)
    current_cost = objective_function(current_bins, bin_capacity)

    best_bins = current_bins
    best_cost = current_cost

    # Lista tabu – przechowuje wcześniej odwiedzane rozwiązania (maks. długość = tabu_size)
    tabu_list = deque(maxlen=tabu_size)

    # Stos zapamiętujący punkty, do których można się cofnąć (punkt bonusowy!)
    backup_stack = []

    for iteration in range(max_iterations):
        neighbours = generate_neighbours(current_bins, bin_capacity)
        random.shuffle(neighbours)  # Losowe przetasowanie

        best_candidate_bins = None
        best_candidate_cost = float('inf')

        for neighbour_bins in neighbours:
            # Klucz do listy tabu sortowanie zeby ignorować permutacje o tej samej wartości
            key = tuple(tuple(sorted(b)) for b in neighbour_bins)
            cost = objective_function(neighbour_bins, bin_capacity)

            # Jeśli rozwiązanie jest w tabu i nie jest wyraźnie lepsze pomijane
            if key in tabu_list and cost >= best_cost * 0.95:
                continue

            # Akceptujemy rozwiązanie jeśli:
            # jest najlepsze z dotychczasowych
            # albo w 5% przypadków "gorsze" dla ucieczki z lokalnego optimum
            if cost < best_candidate_cost or random.random() < 0.05:
                best_candidate_bins = neighbour_bins
                best_candidate_cost = cost

        # Jeśli nie udało się znaleźć żadnego ruchu:
        if best_candidate_bins is None:
            if backup_stack:
                # COFANIE – wracamy do poprzedniego stanu z którego można kontynuować
                current_bins = backup_stack.pop()
                continue
            else:
                # Nie ma już gdzie wrócić – kończymy
                break

        # Zapisanie do mozliwosci cofniecia
        backup_stack.append(current_bins)

        # Przechodzimy do najlepszego znalezionego sąsiada
        current_bins = best_candidate_bins
        current_cost = best_candidate_cost

        # Dodajemy obecne rozwiązanie do listy tabu brak powtarzania
        key = tuple(tuple(sorted(b)) for b in current_bins)
        tabu_list.append(key)

        if current_cost < best_cost:
            best_bins = current_bins
            best_cost = current_cost

        if iteration % 50 == 0:
            tabu_size += 3
            tabu_list = deque(tabu_list, maxlen=tabu_size)

    return best_bins, best_cost

#Wyzazanie
def simulated_annealing_bin_packing(items, bin_capacity, max_iterations=1000,
                                     cooling_schedule=None):
    if cooling_schedule is None:
        raise ValueError("cooling_schedule must be provided (use exponential_cooling or linear_cooling)")

    current_items = items.copy()
    random.shuffle(current_items)

    current_bins = random_solution(current_items, bin_capacity)
    current_cost = objective_function(current_bins, bin_capacity)

    best_bins = current_bins
    best_cost = current_cost

    for k in range(1, max_iterations + 1):
        neighbours = generate_neighbours(current_bins, bin_capacity)
        if not neighbours:
            break

        neighbour_bins = random.choice(neighbours)
        neighbour_cost = objective_function(neighbour_bins, bin_capacity)

        delta = neighbour_cost - current_cost #obliczanie roznicy kosztow i temp
        temperature = cooling_schedule(k) #zmniejszenie temperatury

        if delta < 0 or random.random() < math.exp(-delta / temperature):
            current_bins = neighbour_bins
            current_cost = neighbour_cost

            if current_cost < best_cost:
                best_bins = current_bins
                best_cost = current_cost

    return best_bins, best_cost

def exponential_cooling(T0=100.0, alpha=0.95):
    return lambda k: T0 * (alpha ** k)



#===========Genetyka====================

def pack_items_in_bins(permuted_items, bin_capacity):
    bins = []
    current_bin = []
    current_capacity = 0

    for item in permuted_items:
        if current_capacity + item <= bin_capacity:
            current_bin.append(item)
            current_capacity += item
        else:
            bins.append(current_bin)
            current_bin = [item]
            current_capacity = item

    if current_bin:
        bins.append(current_bin)

    return bins


# KRZYŻOWANIE
def crossover_one_point(parent1, parent2):
    point = random.randint(1, len(parent1) - 2) #bez sensu brac z poczatku i konca
    child = parent1[:point] + [item for item in parent2 if item not in parent1[:point]] #zabezpieczenie przed powtorzeniami
    return child

def crossover_order(parent1, parent2):
    start, end = sorted(random.sample(range(len(parent1)), 2))
    middle = parent1[start:end]
    rest = [item for item in parent2 if item not in middle]
    return rest[:start] + middle + rest[start:]

# MUTACJA
def mutation_swap(individual):
    i, j = random.sample(range(len(individual)), 2)
    individual[i], individual[j] = individual[j], individual[i]
    return individual

def mutation_reverse_segment(individual):
    start, end = sorted(random.sample(range(len(individual)), 2))
    individual[start:end] = reversed(individual[start:end])
    return individual

# WARUNKI ZAKOŃCZENIA
def termination_max_generations(current_generation, max_generations):
    return current_generation >= max_generations

def termination_no_improvement(current_generation, max_generations, best_cost, last_improvement_gen, patience=20):
    return (current_generation - last_improvement_gen) >= patience or current_generation >= max_generations


# SELEKCJA RULETKA
def roulette_selection(fitness_values):
    selection_probs = [1.0 / (f + 1e-6) for f in fitness_values]
    total = sum(selection_probs)
    selection_probs = [p / total for p in selection_probs]

    selected_indexes = []
    for _ in range(len(fitness_values)):
        r = random.random()
        cumulative = 0.0
        for idx, prob in enumerate(selection_probs):
            cumulative += prob
            if r <= cumulative:
                selected_indexes.append(idx)
                break
    return selected_indexes


# ALGORYTM GENETYCZNY
def genetic_algorithm_bin_packing(items, bin_capacity,
                                  population_size=50,
                                  crossover_method='one_point',
                                  mutation_method='swap',
                                  termination='generations',
                                  max_generations=100,
                                  use_elitism=True):

    crossover_functions = {
        'one_point': crossover_one_point,
        'order': crossover_order
    }
    mutation_functions = {
        'swap': mutation_swap,
        'reverse': mutation_reverse_segment
    }
    termination_functions = {
        'generations': termination_max_generations,
        'no_improvement': termination_no_improvement
    }

    crossover = crossover_functions[crossover_method]
    mutate = mutation_functions[mutation_method]
    should_terminate = termination_functions[termination]

    expected_items_count = len(items)

    # Inicjalizacja populacji
    population = [random.sample(items, len(items)) for _ in range(population_size)]
    population_fitness = [
        objective_function(pack_items_in_bins(ind, bin_capacity), bin_capacity, expected_items_count)
        for ind in population
    ]

    best_solution = population[population_fitness.index(min(population_fitness))]
    best_cost = min(population_fitness)
    last_improvement_gen = 0

    for generation in range(max_generations):
        selected_indexes = roulette_selection(population_fitness)
        next_population = []

        if use_elitism:
            next_population.append(best_solution)

        while len(next_population) < population_size:
            parent1 = population[random.choice(selected_indexes)]
            parent2 = population[random.choice(selected_indexes)]
            child = crossover(parent1, parent2)

            if random.random() < 0.1:
                child = mutate(child)

            next_population.append(child)

        population = next_population
        population_fitness = [
            objective_function(pack_items_in_bins(ind, bin_capacity), bin_capacity, expected_items_count)
            for ind in population
        ]

        current_best_cost = min(population_fitness)
        current_best_solution = population[population_fitness.index(current_best_cost)]

        if current_best_cost < best_cost:
            best_cost = current_best_cost
            best_solution = current_best_solution
            last_improvement_gen = generation

        if termination == 'generations':
            if should_terminate(generation, max_generations=max_generations):
                break
        elif termination == 'no_improvement':
            if should_terminate(generation, max_generations=max_generations,
                                best_cost=best_cost, last_improvement_gen=last_improvement_gen):
                break

    final_bins = pack_items_in_bins(best_solution, bin_capacity)
    final_bins = [b for b in final_bins if b]
    return final_bins, objective_function(final_bins, bin_capacity)

def main(items, bin_capacity, max_iterations=1000):
    print("=== Bin Packing Problem ===")
    print(f"Items: {items}")
    print(f"Bin capacity: {bin_capacity}")
    print("---------------------------")

    # Random Solution
    bins_random = random_solution(items, bin_capacity)
    cost_random = objective_function(bins_random, bin_capacity)
    print(f"Random Solution | Liczba pojemników: {len(bins_random)}, Koszt: {cost_random}")
    print(bins_random)
    print("---------------------------")

    # Hill Climbing (Best Neighbour)
    bins_hc_best, cost_hc_best = hill_climbing_bin_packing(items, bin_capacity, max_iterations)
    print(f"Hill Climbing (Best Neighbour) | Liczba pojemników: {len(bins_hc_best)}, Koszt: {cost_hc_best}")
    print(bins_hc_best)
    print("---------------------------")

    # Hill Climbing (Stochastic)
    bins_hc_random, cost_hc_random = stochastic_hill_climbing_bin_packing(items, bin_capacity, max_iterations)
    print(f"Hill Climbing (Random Neighbour) | Liczba pojemników: {len(bins_hc_random)}, Koszt: {cost_hc_random}")
    print(bins_hc_random)
    print("---------------------------")

    # Tabu Search
    bins_tabu, cost_tabu = tabu_search_bin_packing(items, bin_capacity, tabu_size=5, max_iterations=max_iterations)
    print(f"Tabu Search | Liczba pojemników: {len(bins_tabu)}, Koszt: {cost_tabu}")
    print(bins_tabu)
    print("---------------------------")

    # Brute Force
    if len(items) <= 10:
        bins_brute, cost_brute = brute_force_optimal_bin_packing(items, bin_capacity)
        print(f"Brute Force | Liczba pojemników: {len(bins_brute)}, Koszt: {cost_brute}")
        print(bins_brute)
    else:
        print("Brute Force pominięty (problem zbyt duży)")

    # Simulated Annealing
    cooling = exponential_cooling(T0=100.0, alpha=0.95)
    bins_sa, cost_sa = simulated_annealing_bin_packing(items, bin_capacity,
                                                       max_iterations=max_iterations,
                                                       cooling_schedule=cooling)
    print(f"Simulated Annealing | Liczba pojemników: {len(bins_sa)}, Koszt: {cost_sa}")
    print(bins_sa)
    print("---------------------------")


    # Genetic Algorithm
    bins_ga, cost_ga = genetic_algorithm_bin_packing(
        items,
        bin_capacity,
        population_size=50,
        crossover_method='order',
        mutation_method='reverse',
        termination='no_improvement',
        max_generations=max_iterations,
        use_elitism=True
    )
    print(f"Genetic Algorithm | Liczba pojemników: {len(bins_ga)}, Koszt: {cost_ga}")
    print(bins_ga)
    print("---------------------------")


def load_items_from_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
        items = [int(x) for x in content.replace(',', ' ').split()]
    return items

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Bin Packing Problem")

    parser.add_argument('--file', type=str, help="Plik z przedmiotami do zapakowania")
    parser.add_argument('--items', type=str, help="Przedmioty jako tekst, np. '3,7,4,6,5'")
    parser.add_argument('--bin_capacity', type=int, help="Pojemność jednego pojemnika")
    parser.add_argument('--max_iterations', type=int, default=1000, help="Liczba iteracji (domyślnie 1000)")

    args = parser.parse_args()

    if args.file:
        if not os.path.exists(args.file):
            print(f"Plik '{args.file}' nie istnieje.")
            sys.exit(1)
        items = load_items_from_file(args.file)
    elif args.items:
        items = [int(x) for x in args.items.replace(',', ' ').split()]
    else:
        print("Nie podano danych – używam domyślnych.")
        items = [3, 7, 4, 6, 5, 8, 2, 1, 3, 9] * 5

    bin_capacity = args.bin_capacity or 10
    max_iterations = args.max_iterations

    main(items, bin_capacity, max_iterations)
