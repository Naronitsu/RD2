package rd2.server.service;

import java.util.LinkedHashMap;
import java.util.Map;

public class RvResult {
    public long rowsProcessed;
    public long elapsedMs;
    public double cpuTimeMs;
    public long heapUsedBeforeBytes;
    public long heapUsedAfterBytes;
    public long heapDeltaBytes;
    public boolean rvEnabled;
    public Map<String, Long> flags = new LinkedHashMap<String, Long>();
}
