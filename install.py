from multiprocessing import Queue
from subprocess import Popen, PIPE
from typing import List

import pexpect

import classes

def install_platform(q: Queue, instance_list: List[classes.Instance], password: str):
    """Installs platform and updates progress bar as processes are finished"""
    print(instance_list)
    q.put_nowait(20)  # Update progress bar

    ## Host Configuration; handles password input; Assumes password was entered correctly
    # host_config_process = pexpect.spawn("ansible-playbook -K -i inventory.yml --connection=local volttron.deployment.host_config")
    # host_config_process.expect("BECOME password: ")
    # host_config_process.sendline(password)

    # host_config_process.expect(pexpect.EOF)
    # print(host_config_process.before.decode())
    # q.put_nowait(40)

    ## Install Platform
    # install_cmd = Popen(['bash', '-c', 'ansible-playbook -i inventory.yml --connection=local volttron.deployment.install_platform'], stdout=PIPE, stderr=PIPE)
    # stdout, stderr = install_cmd.communicate()

    # if stdout is not None:
    #    stdout_str = stdout.decode('utf-8')
    #    print(stdout_str)
    # if stderr is not None:
    #    stderr_str = stderr.decode('utf-8')
    #    print(stderr_str)

    # q.put_nowait(60)

    ## Run Platform
    # run = Popen(['bash', '-c', 'ansible-playbook -i inventory.yml --connection=local volttron.deployment.run_platforms -vvv'])
    # stdout, stderr = run.communicate()
    #
    # if stdout is not None:
    #    stdout_str = stdout.decode("utf-8")
    #    print(stdout_str)
    # if stderr is not None:
    #    stderr_str = stderr.decode("utf-8")
    #    print(stderr_str)

    # q.put_nowait(80)

    ## Configure Agents
    # configure = Popen(['bash', '-c', 'ansible-playbook -i inventory.yml --connection=local volttron.deployment.configure_agents -vvv'])
    # stdout, stderr = configure.communicate()
    #
    # if stdout is not None:
    #    stdout_str = stdout.decode('utf-8')
    #    print(stdout_str)
    # if stderr is not None:
    #    stderr_str = stderr.decode('utf-8')
    #    print(stderr_str)

    # q.put_nowait(100)