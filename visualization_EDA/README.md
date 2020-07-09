READ NEB_Project.pdf

`ts_data/` should have some data samples used to generate `tapestation.db`.  If you want to generate a SQL table use `gen_SQL.ipynb`.  But running the code should be as simple as going into the folder of `py_code/` then running `python3 neb_interface.py`, and going into a browser and accessing the port (no need to do all the fancy stuff for server, it was necessary for the project to run).

Looking back at it now, should've made a makefile or deployed with Docker to not worry about dependencies.
