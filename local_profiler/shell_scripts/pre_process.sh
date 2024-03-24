echo "make preparations for profiling process"
sysctl kernel.perf_event_paranoid=1
sysctl kernel.kptr_restrict=0