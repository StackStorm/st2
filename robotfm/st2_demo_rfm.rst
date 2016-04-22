.. default-role:: code

=====================================
  Robot Framework st2 demo
=====================================

A very basic demo on how to write test cases for st2 using Robot Framework

Executing this guide
====================

Install following modules::


    pip install robotframework
    pip install docutils


Command to execute this test suite::


    pybot st2_rfm_demo.rst

Test cases
==========

Robot Framework test cases are created using a simple tabular syntax. For
example, the following table has two tests:

- Check "packs.virtualenv_prerun" in st2 action list
- Add/Delete key value in the key value store

.. code:: robotframework

    #*** Variables ***
    #${NAME}  \"new\"

    *** Test Cases ***
    Check packs.virtualenv_prerun in st2 action list
        ${result}=         Run Process        st2  action  list  -j
        Log To Console     \n${result.stdout}
        Should Contain     ${result.stdout}   packs.virtualenv_prerun

    Add/Delete key value in the key value store
        ${result}=         Run Process        st2  key  set  new  life  -j
        Log To Console     SET: \n${result.stdout}
        ${result}=         Run Process        st2  key  list  -j
        Log To Console     LIST: \n${result.stdout}
        Should Contain     ${result.stdout}   "name": ${NAME}
        ${result}=         Run Process        st2  key  delete  new  -j
        Log To Console     DELETE: \n${result.stdout}
        Should Contain     ${result.stdout}   Resource with id ${NAME} has been successfully deleted.


Settings, Keywords and Variables
================================

There are two sources of keywords `Library Keywords` and `User Defined Keywords`
Tests in this guide need keywords from the standard `Process` library

Also `Variables` can either be in either in the this file in section \*\*\* Variables \*\*\*
(as shown in the test cases section, but commented out) or it can be in a seperate yaml file
and can be called via settings section as shown below

.. code:: robotframework

    *** Settings ***
    Library             Process
    Variables           variables/st2_rfm_demo.yaml

Contents of "variables/st2_rfm_demo.yaml" file::


    NAME:  '"new"'
  
  
For more details refer: 
`Robot Framework User Guide`_.


.. _Robot Framework User Guide: http://robotframework.org/robotframework/#user-guide
