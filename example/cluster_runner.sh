#!/bin/sh

if [ -z "${QUEUE}" ]
then
	echo "You forgot to set the QUEUE"
	exit 1
fi

job_name=rosenbrock_test
cmd="/scisoft/EPD/7.3.2/bin/python rosenbrock.py --x \"$1\" --y \"$2\" --wait 0.1"

job_id=`qsub -terse -cwd -j yes -sync y -l ${QUEUE} -N ${job_name} -b yes ${cmd} | head -n 1`

job_id_file=${job_name}.o${job_id}
cat ${job_id_file}
