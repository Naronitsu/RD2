package rd2.server.service;

import bridge.EcuSample;
import bridge.JavaMonitorBridge;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class RvCsvService {

    private static final String FLAG_VOLTAGE = "voltageOutOfRange";
    private static final String FLAG_COOLANT = "coolantTooHigh";
    private static final String FLAG_THROTTLE = "throttleSpike";
    private static final String FLAG_LOAD_MAP = "loadMapMismatch";

    private final boolean defaultRvEnabled;

    public RvCsvService(@Value("${rv.enabled:true}") boolean defaultRvEnabled) {
        this.defaultRvEnabled = defaultRvEnabled;
    }

    public RvResult analyze(MultipartFile file) throws IOException {
        return analyze(file, null);
    }

    public RvResult analyze(MultipartFile file, Boolean rvEnabledOverride) throws IOException {
        boolean rvEnabled = rvEnabledOverride != null ? rvEnabledOverride.booleanValue() : defaultRvEnabled;
        long startNs = System.nanoTime();

        BufferedReader reader = new BufferedReader(
            new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8)
        );

        String header = reader.readLine();
        if (header == null) {
            throw new IOException("CSV file is empty");
        }

        Map<String, Integer> idx = indexColumns(header);
        validateColumns(idx);

        RvResult result = new RvResult();
        result.rvEnabled = rvEnabled;
        result.flags.put(FLAG_VOLTAGE, 0L);
        result.flags.put(FLAG_COOLANT, 0L);
        result.flags.put(FLAG_THROTTLE, 0L);
        result.flags.put(FLAG_LOAD_MAP, 0L);

        String line;
        while ((line = reader.readLine()) != null) {
            if (line.trim().isEmpty()) {
                continue;
            }
            String[] p = line.split(",", -1);
            EcuSample s = parseSample(p, idx);
            result.rowsProcessed++;
            if (rvEnabled) {
                String violation = JavaMonitorBridge.onSample(s);
                if (violation != null && result.flags.containsKey(violation)) {
                    bump(result, violation);
                }
            }
        }

        result.elapsedMs = (System.nanoTime() - startNs) / 1_000_000L;
        return result;
    }

    private static void bump(RvResult result, String key) {
        result.flags.put(key, result.flags.get(key) + 1L);
    }

    private static Map<String, Integer> indexColumns(String headerLine) {
        String[] cols = headerLine.split(",", -1);
        Map<String, Integer> map = new HashMap<String, Integer>();
        for (int i = 0; i < cols.length; i++) {
            map.put(cols[i].trim(), i);
        }
        return map;
    }

    private static void validateColumns(Map<String, Integer> idx) throws IOException {
        require(idx, "ThrottlePosition");
        require(idx, "EngineRunningTime");
        require(idx, "Load");
        require(idx, "MAPSource");
        require(idx, "RPM");
        require(idx, "BatteryVoltage_V");
        require(idx, "CoolantTemp_C");
    }

    private static void require(Map<String, Integer> idx, String col) throws IOException {
        if (!idx.containsKey(col)) {
            throw new IOException("Missing required CSV column: " + col);
        }
    }

    private static EcuSample parseSample(String[] row, Map<String, Integer> idx) {
        EcuSample s = new EcuSample();
        s.ThrottlePosition = parseDouble(row[idx.get("ThrottlePosition")]);
        s.EngineRunningTime = parseDouble(row[idx.get("EngineRunningTime")]);
        s.Load = parseDouble(row[idx.get("Load")]);
        s.MAPSource = parseDouble(row[idx.get("MAPSource")]);
        s.RPM = parseDouble(row[idx.get("RPM")]);
        s.BatteryVoltage_V = parseDouble(row[idx.get("BatteryVoltage_V")]);
        s.CoolantTemp_C = parseDouble(row[idx.get("CoolantTemp_C")]);
        return s;
    }

    private static double parseDouble(String v) {
        if (v == null || v.isEmpty()) {
            return 0.0;
        }
        return Double.parseDouble(v);
    }
}
