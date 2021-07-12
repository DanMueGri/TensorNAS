def TestEASimple(
    cxpb,
    mutpb,
    pop_size,
    gen_count,
    gen_individual,
    evaluate_individual,
    crossover_individual,
    mutate_individual,
    objective_weights,
    test_name,
    verbose=False,
    filter_function=None,
    filter_function_args=None,
    save_individuals=True,
    comment=None,
    multithreaded=True,
    log=True,
):
    from tensornas.tools.DEAPtest import DEAPTest

    test = DEAPTest(
        pop_size=pop_size,
        gen_count=gen_count,
        f_gen_individual=gen_individual,
        objective_weights=objective_weights,
        multithreaded=multithreaded,
    )

    test.set_evaluate(func=evaluate_individual)
    test.set_mate(func=crossover_individual)
    test.set_mutate(func=mutate_individual)

    from deap import tools

    test.set_select(func=tools.selTournamentDCD)

    pop, logbook = eaSimple(
        population=test.pop,
        toolbox=test.toolbox,
        cxpb=cxpb,
        mutpb=mutpb,
        ngen=gen_count,
        test_name=test_name,
        stats=test.stats,
        halloffame=test.hof,
        verbose=verbose,
        individualrecord=test.ir,
        save_individuals=save_individuals,
        filter_function=filter_function,
        filter_function_args=filter_function_args,
        log=log,
    )

    test.ir.save(
        1,
        test_name=test_name,
        title=filter_function.__name__ if filter_function else "no filter func",
        comment=comment,
    )

    return pop, logbook, test


def eaSimple(
    population,
    toolbox,
    cxpb,
    mutpb,
    ngen,
    test_name,
    stats=None,
    halloffame=None,
    verbose=__debug__,
    individualrecord=None,
    save_individuals=False,
    filter_function=None,
    filter_function_args=None,
    log=True,
):
    """This algorithm reproduce the simplest evolutionary algorithm as
    presented in chapter 7 of [Back2000]_.
    :param population: A list of individuals.
    :param toolbox: A :class:`~deap.base.Toolbox` that contains the evolution
                    operators.
    :param cxpb: The probability of mating two individuals.
    :param mutpb: The probability of mutating an individual.
    :param ngen: The number of generation.
    :param stats: A :class:`~deap.tools.Statistics` object that is updated
                  inplace, optional.
    :param halloffame: A :class:`~deap.tools.HallOfFame` object that will
                       contain the best individuals, optional.
    :param verbose: Whether or not to log the statistics.
    :returns: The final population
    :returns: A class:`~deap.tools.Logbook` with the statistics of the
              evolution
    The algorithm takes in a population and evolves it in place using the
    :meth:`varAnd` method. It returns the optimized population and a
    :class:`~deap.tools.Logbook` with the statistics of the evolution. The
    logbook will contain the generation number, the number of evaluations for
    each generation and the statistics if a :class:`~deap.tools.Statistics` is
    given as argument. The *cxpb* and *mutpb* arguments are passed to the
    :func:`varAnd` function. The pseudocode goes as follow ::
        evaluate(population)
        for g in range(ngen):
            population = select(population, len(population))
            offspring = varAnd(population, toolbox, cxpb, mutpb)
            evaluate(offspring)
            population = offspring
    As stated in the pseudocode above, the algorithm goes as follow. First, it
    evaluates the individuals with an invalid fitness. Second, it enters the
    generational loop where the selection procedure is applied to entirely
    replace the parental population. The 1:1 replacement ratio of this
    algorithm **requires** the selection procedure to be stochastic and to
    select multiple times the same individual, for example,
    :func:`~deap.tools.selTournament` and :func:`~deap.tools.selRoulette`.
    Third, it applies the :func:`varAnd` function to produce the next
    generation population. Fourth, it evaluates the new individuals and
    compute the statistics on this population. Finally, when *ngen*
    generations are done, the algorithm returns a tuple with the final
    population and a :class:`~deap.tools.Logbook` of the evolution.
    .. note::
        Using a non-stochastic selection method will result in no selection as
        the operator selects *n* individuals from a pool of *n*.
    This function expects the :meth:`toolbox.mate`, :meth:`toolbox.mutate`,
    :meth:`toolbox.select` and :meth:`toolbox.evaluate` aliases to be
    registered in the toolbox.
    .. [Back2000] Back, Fogel and Michalewicz, "Evolutionary Computation 1 :
       Basic Algorithms and Operators", 2000.
    """
    if log:
        from tensornas.tools.logging import Logger

        logger = Logger(test_name)

    from deap import tools

    logbook = tools.Logbook()
    logbook.header = ["gen", "nevals"] + (stats.fields if stats else [])

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    if save_individuals:
        fitnesses = toolbox.map(
            toolbox.evaluate,
            [(ii, test_name, 0, i) for i, ii in enumerate(invalid_ind)],
        )
    else:
        fitnesses = toolbox.map(
            toolbox.evaluate, [(ii, None, None, None) for ii in invalid_ind]
        )

    for count, (ind, fit) in enumerate(zip(invalid_ind, fitnesses)):
        ind.block_architecture.param_count = fit[-2]
        ind.block_architecture.accuracy = fit[-1]

        if filter_function:
            if filter_function_args:
                ind.fitness.values = filter_function(fit, filter_function_args)
            else:
                ind.fitness.values = filter_function(fit)
        else:
            ind.fitness.values = fit

        if hasattr(ind, "updates"):
            ind.updates.append(
                (ind.block_architecture.param_count, ind.block_architecture.accuracy)
            )
        else:
            ind.updates = [
                (ind.block_architecture.param_count, ind.block_architecture.accuracy)
            ]

    from deap.tools.emo import assignCrowdingDist

    assignCrowdingDist(population)

    if individualrecord:
        individualrecord.add_gen(population)

    if halloffame is not None:
        halloffame.update(population)

    record = stats.compile(population) if stats else {}
    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    if verbose:
        print(logbook.stream)

    # Begin the generational process
    for gen in range(1, ngen + 1):

        if log:
            logger.log("Gen #{}, population: {}".format(gen, len(population)))

        # Select the next generation individuals
        offspring = toolbox.select(population, len(population))

        # Vary the pool of individuals
        from deap.algorithms import varAnd

        offspring = varAnd(offspring, toolbox, cxpb, mutpb)

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        if save_individuals:
            fitnesses = toolbox.map(
                toolbox.evaluate,
                [(ii, test_name, gen, i) for i, ii in enumerate(invalid_ind)],
            )
        else:
            fitnesses = toolbox.map(
                toolbox.evaluate, [(ii, None, None, None) for ii in invalid_ind]
            )

        for count, (ind, fit) in enumerate(zip(invalid_ind, fitnesses)):
            ind.block_architecture.param_count = fit[-2]
            ind.block_architecture.accuracy = fit[-1]

            if filter_function:
                if filter_function_args:
                    ind.fitness.values = filter_function(fit, filter_function_args)
                else:
                    ind.fitness.values = filter_function(fit)

            if hasattr(ind, "updates"):
                ind.updates.append(
                    (
                        ind.block_architecture.param_count,
                        ind.block_architecture.accuracy,
                    )
                )
            else:
                ind.updates = [
                    (
                        ind.block_architecture.param_count,
                        ind.block_architecture.accuracy,
                    )
                ]

        assignCrowdingDist(offspring)

        # Update the hall of fame with the generated individuals
        if halloffame is not None:
            halloffame.update(offspring)

        # Replace the current population by the offspring
        population[:] = offspring

        if individualrecord:
            individualrecord.add_gen(population)

        if log:
            for x, ind in enumerate(population):
                logger.log(
                    "Ind #{}, params:{}, acc:{}%".format(
                        x,
                        ind.block_architecture.param_count,
                        ind.block_architecture.accuracy,
                    )
                )
                logger.log(str(ind))

        # Append the current generation statistics to the logbook
        record = stats.compile(population) if stats else {}
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        if verbose:
            print(logbook.stream)

    if log:
        logger.log("STOP")

    return population, logbook
