echo "make preparations for profiling container"
sysctl kernel.perf_event_paranoid=1
sysctl kernel.kptr_restrict=0

CONTAINER_ID=${1}

LOCAL_LIB_DIR=${2}
LOCAL_LIB_PATH="${LOCAL_LIB_DIR}/libasyncProfiler.so"

echo "local lib path: ${LOCAL_LIB_PATH}"

docker exec $CONTAINER_ID rm -rf $LOCAL_LIB_DIR
docker exec $CONTAINER_ID mkdir -p $LOCAL_LIB_DIR
docker cp ${LOCAL_LIB_PATH} ${CONTAINER_ID}:${LOCAL_LIB_DIR}

echo "docker exec ${CONTAINER_ID} mkdir -p ${LOCAL_LIB_DIR}"
echo "docker cp ${LOCAL_LIB_PATH} ${CONTAINER_ID}:${LOCAL_LIB_PATH}"

#获取本地so目录
#在container创建so目录

#注意确保profile时container的jvm正在运行
#docker top获取容器内的jvm pid