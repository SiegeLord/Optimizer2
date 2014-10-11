## What is Optimizer2?

Optimizer2 is a command line tool that will attempt to minimize a user 
defined function that maps a real vector into a scalar. The function to 
be minimized is defined by creating a program that receives the 
arguments on the command line, and writes the function result to 
standard output. Optimizer2 will invoke this program multiple times 
with different values of the arguments in order to attempt to find a 
minimum. The function can be anything that satisfies the above 
requirements. It can be a scientific model with a set of parameters 
that you want to search over, or it could be AI model for a game that 
needs some parameters tweaked. Many problems can be posed as those of 
function minimization, and this tool aims to make the actual step of 
minimization relatively simple. This guide will use terms 'minimize' and 
'optimize' interchangeably.

Note, that for historical reasons, this software is called Optimizer2, but the 
actual executable name is `optimizer`.

There are four steps that you tend to take when optimizing a function:

1. Create a program that takes the function arguments via the command 
   line and outputs the function result to standard output.
2. Create a configuration file for Optimizer2 that describes how to 
   interface with your program, and specifies the optimization algorithm.
3. Run the optimization.
4. Examine the results and possibly repeat steps 1-3.

This guide will cover these steps.

## Installation

Optimizer2 is written in [Python](https://www.python.org/downloads/), and 
requires Python version 2.7 or later (but not 3.x).

### Installation Using `pip`

Typically, [pip](https://pip.pypa.io/en/latest/) is only easily available on Linux.

* If you have administrator privileges, run:

        sudo pip install optimizer2

* If you don't, run:

        pip install optimizer2

### Manual Installation

1. Download the latest release from 
   [here](https://pypi.python.org/pypi/optimizer2) (see the source link towards 
   the bottom) and extract it somewhere.
2. Open a terminal and navigate to where you extracted it. This directory 
   should have the `README` and other files.
3. Install it

    * If you are on Windows, run:

            python setup.py install

    * If you have administrator privileges on a UNIX-like system (e.g. Mac 
      OSX), run:

            sudo python setup.py install
    
    * If you don't have administrator privileges on a UNIX-like system, run:
    
            python setup.py install --prefix $HOME

    This will install it into your home folder. This assumes that you've set 
    things up to run programs from it (e.g. added `$HOME/bin` to `PATH` and 
    amended `PYTHONPATH`)

### Verifying The Installation

Run this command:

```bash
optimizer --version
```

This should output the version of Optimizer2 that you've installed. On Windows, 
you may need to invoke it using a slightly more verbose invocation like this:

```bash
python C:\Python27\Scripts\optimizer --version
```

## Basic Usage

This section will assume that you have a UNIX-like environment available (on 
Windows you can obtain one from the
[MSYS2 project](http://sourceforge.net/projects/msys2/)).

### Writing a Program to be Optimized

To be compatible with Optimizer2, your program must be able to take arguments 
via the command line and output the quantity to be minimized to standard 
output. For example, let's say that you want to minimize the
[Rosenbrock function](http://en.wikipedia.org/wiki/Rosenbrock_function). Here is
an example C program that implements this function and is compatible with 
Optimizer2:

```c
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char** argv)
{
    // Make sure we have two arguments
    if(argc < 3)
        return -1;
    // Read the first argument
    double x = atof(argv[1]);
    // Read the second argument
    double y = atof(argv[2]);
    // Compute the function value
    double rosenbrock = 100.0 * ((y - x * x) * (y - x * x))
                        + (1.0 - x) * (1.0 - x);
    printf("Result: %f\n", rosenbrock); // Print it to standard output
}
```

After compiling this with your favorite C compiler, you can test this program 
on the command line:

    $ ./rosenbrock 1.0 1.0
    Result: 0.000000

When passed to `optimizer`, it will call this program in much the same way and 
then parse the standard output (specifically it will look for the `Result: xxxxx`
line) and attempt to minimize it by varying the argument values. `optimizer` may
run these programs in parallel, but there is no chance of the standard outputs
getting mixed up.

See [Advanced Usage](#advanced-usage) section for more tips on writing these programs.

### Configuring the Optimization Run

Optimizer2 requires a configuration file to describe your optimization problem. 
We will first show a complete configuration file and then go through it line by 
line. Here is a configuration file that interfaces with the above C code for 
the Rosenbrock function:

```ini
[options]
command      = ./rosenbrock {0} {1}
num_args     = 2
limit0       = [-5, 5]
limit1       = [-5, 5]
result_re    = Result: (.*)
max_launches = 2
algorithm    = de

[de]
pop_size     = 20
cross        = 0.9
max_gen      = 50
strategy     = rand
init0        = [0.5, 0.5]
```

The configuration file uses the [INI file format](https://en.wikipedia.org/wiki/INI_file).

#### General Options

The `[options]` section describes the optimization problem.


```ini
command = ./rosenbrock {0} {1}
```

This specifies how `optimizer` should invoke your program. First, it naturally 
contains the name of your program (prefixed with `./` as it will try to launch 
it from the same directory that it was invoked from, see next section). The 
special `{#}` syntax signifies where the argument values will be pasted in. 
That is, the first argument will be placed where `{0}` appears, second argument 
will be placed where `{1}` appears and so on. You can place other arguments 
when specifying the value of `command`. For example, if your program accepts an 
argument named `--fast` it is perfectly legal for `command` to be 
`./your_program --fast {0} {1}`. Note that the program is not ran in a shell, 
so this command, for example, won't do what you might expect: `./your_program 
{0} {1} --data-files data/*`.


```ini
num_args = 2
limit0   = [-5, 5]
limit1   = [-5, 5]
```

This describes the number of arguments `num_args` and their limits. The limits 
are described using the `limit# = [min, max]` syntax, where `#` is the relevant 
argument index. The minimum and maximum are inclusive. Take extra care to make 
sure `num_args` matches the number of arguments you described in the `command` 
value and the number of `limit#` values.


```ini
result_re = Result: (.*)
```

This describes what `optimizer` will look for in the standard output of your 
program to determine what to minimize. The value of this option is a [regular 
expression](https://docs.python.org/2/library/re.html#regular-expression-syntax) 
with a single capture group (in this case, this is the `(.*)` part of the 
regular expression). The text captured by the capture group will be interpreted 
as a decimal fraction. Exponential syntax (e.g. `1.0e5`) is supported. 
Typically, the value for this option will be some identifying text that won't 
be confused with other output of your program (in this case, `Result: `, but 
otherwise it can be anything) followed by the capture group. `optimizer` will 
use this regular expression on each line of the standard output of your 
program.


```ini
max_launches = 2
```

This specifies how many instances of your program `optimizer` will launch in 
parallel. If omitted, it will be set to 1.


```ini
algorithm = de
```

This specifies which algorithm will be used to optimize your program. 
Currently, there are two choices:

* `de` - Differential evolution, a classic, general purpose optimization 
algorithm.
* `cont_de` - Continuous differential evolution, a continuous extension of the 
algorithm.

Whichever one you choose, `optimizer` will expect an option section with the 
same name later in the configuration file in this case, it will expect the `de` 
section). The commonly used differential evolution algorithm will be described 
below, while the more special purpose continuous variant is described in the 
[Continuous Differential Evolution](#continuous-differential-evolution) section below.

#### Differential Evolution

[Differential evolution](http://en.wikipedia.org/wiki/Differential_evolution) 
is a good, general purpose optimization algorithm. In gross terms, it optimizes 
your function by maintaining a population of function argument sets with their 
associated function values, and it creates new candidate arguments by 
combining them using a particular stochastic crossover strategy. The algorithm 
proceeds in generations, where the entire population is potentially refreshed 
with new candidates, if they are better. The options for this algorithm are set 
in the `de` section.


```ini
pop_size = 20
```

This specifies the population size. The rule of thumb for this value is to set 
it to be 10 times the number of function arguments you have (since the 
Rosenbrock function has only 2 arguments, we choose a population size of 20), 
but limit it to 40. Note that the worst failure mode of differential evolution 
is population diversity crash (i.e. premature convergence), so going for more 
is better if you can afford it. The initial argument values are picked 
uniformly from the argument limits specified in the general options.


```ini
cross = 0.9
```

This specifies the crossover probability. Low crossover results in coordinate 
ascent-style parameter trajectories, while high crossover is more useful for 
situations with parameter dependence. 0.9 is a reasonable midway point 
suggested by the algorithm authors.


```ini
max_gen = 50
```

This specifies the maximum number of generations to simulate. Each generation 
involves `pop_size` number of function evaluations.


```ini
strategy = rand
```

This specifies the cross-over strategy. There are two choices here:

* `rand` - The 'DE/rand/1/bin' method from the algorithm description. In gross 
terms, this chooses random argument sets when creating new candidates.

* `best` - The 'DE/best/1/bin' method from the algorithm description. In gross 
terms, this, in addition to what 'DE/rand/1/bin' does, also takes into account 
the best argument set in the current population.

`rand` seems to work well in many cases.


```ini
init0 = [0.5, 0.5]
```

It is possible to seed the initial population with some argument values. These 
follow the following syntax: `init# = [arg1, arg2, ...]`, where `#` is the 
initial argument set index (you have to start at zero and count up), while the 
array to the right of `=` specifies the actual values. Make sure the number of 
values matches what you specified in the general options.

### Running the Optimization

Once you've got everything ready, running the optimization is simple. Just 
invoke `optimizer` with your configuration file as an argument:

```bash
optimizer rosenbrock.cfg
```

Note that `optimizer` will output everything about the optimization run to to 
standard output, so in practice it helps to redirect it somewhere for later 
analysis. The `tee` command is particularly useful here:

```bash
optimizer rosenbrock.cfg | tee optimization_output
```

Monitoring the run is a bit complicated by the fact that Python likes 
to buffer the standard output (i.e. it won't output anything until a certain 
amount is written). Thus, in practice, it is better to run optimizer via 
Python, like this:

```bash
python -u $(which optimizer) rosenbrock.cfg | tee optimization_output
```

The `-u` flag in particular turns off the buffering behavior mentioned above.

## Advanced Usage

This section describes some of the more rarely used features of Optimizer2, as 
well as a few tips and tricks.

### Additional Parameters for Differential Evolution

* `min_var` - Normally optimization stops only when the maximum number of 
generations is reached (specified by the `max_gen` parameter). The population 
geometric mean of variances of each of the function arguments can be used as a 
stopping condition. This parameter specifies the value of that average, which, 
when reached causes the optimization to stop.

* `factor` - This specifies the weighting factor for the algorithm. If 
ommitted, it is chosen randomly from the range `[0.5, 1.0]` each generation as 
suggested by the algorithm authors.

### Continuous Differential Evolution

Continuous differential evolution is an extension of the usual differential 
evolution to make it more efficient on massively parallel systems. The standard 
differential evolution algorithm simulates all the candidate argument sets in a 
generation before generating more candidates. On systems which can simulate all 
of a generation in parallel, the possible variability in the simulation time of 
the individual argument sets becomes a source of inefficiency. For example, one 
parameter set may take a much longer time to simulate than all others, which 
would imply that much of the parallelism afforded by the system will be wasted.

Continuous differential evolution side-steps this by avoiding the concept of a 
generation, and instead generates the candidate argument sets continuously. 
That is, as soon as one candidate finishes evaluating, another one is 
generated. This greatly increases the utilization of the parallel system. Note 
that the initial set of parameters must be evaluated to completion, so if you 
are optimizing a function with a very large variability in run time, the very 
first 'generation' will take as long as the slowest evaluation.

This does not come for free, however as this algorithm biases against the 
slower function evaluations. Make sure that function evaluation time is either 
uncorrelated or anti-correlated with the function value (i.e. smaller function 
values take less time to compute and will thus be naturally selected for).

This algorithm's parameters are declared in the `[cont_de]` section. It 
shares the following parameters with differential evolution:

* `pop_size` - Population size
* `factor` - Weighting factor
* `cross` - Crossover probability
* `min_var` - Minimum population geometric mean of the function arguments
* `init#` - Initial argument sets

The new parameter is:

```
max_trials
```

Since continuous differential evolution doesn't have generations, the default 
stopping condition is the number of function evaluations.

### Adapting an Existing Program

Often, you do not have the option to write a brand new program for each 
optimization program. This typically happens when you have several separate 
programs that must run in sequence before you can evaluate the function. For 
this, you generally use a (bash) script. For example, this program will execute 
two different programs, analyze their outputs and then finally print out a 
function value:

```bash
#!/bin/bash

# Create two temporary files to capture the output of program_1 and program_2
file_1=$(mktemp)
file_2=$(mktemp)

# Run the two programs with all the arguments, and capture their outputs
./program_1 $@ > $file_1
./program_2 $@ > $file_2

# Analyze the programs' output. This program will actually print something to
# standard output for optimizer to read
./analyze $file_1 $file_2
```

### Passing Arguments to Your Program Without Modifying the Configuration File

Occasionally, it is useful to send additional arguments to your program without 
modifying the configuration script each time you make that change. The easiest 
way to do this is to use 
[environment variables](http://en.wikipedia.org/wiki/Environment_variable). 
This typically requires you to wrap your program in a (bash) script. For 
example, let's say you want to pass two arguments to your program, named `ARG1` 
and `ARG2`. To do this, you would invoke `optimizer` like so:

```bash
ARG1=-a ARG2=-b optimizer optimization.cfg > optimization_report
```

To access the values from the wrapper script, you would simply expand those two 
variable names. E.g:

```bash
echo $ARG1
echo $ARG2
```
will print

    -a
    -b

It is possible to access these variables from your program as well, as all 
programming languages allow you to get the value of the environment variables.

