#!/bin/bash

cwd=`dirname "${0}"`
expr "${0}" : "/.*" > /dev/null || cwd=`(cd "${cwd}" && pwd)`
cd $cwd/..

source venv/bin/activate
python -m app.recruiter --spec > app/spec_recruiter.json
python -m app.commander --spec > app/spec_commander.json
python -m app.leader --spec > app/spec_leader.json
