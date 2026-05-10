package bridge;

import larva._cls_ecu_flags0;

public final class JavaMonitorBridge {
    private static final Object INIT_LOCK = new Object();

    private JavaMonitorBridge() {
    }

    private static void ensureInitialized() {
        if (_cls_ecu_flags0._cls_ecu_flags0_instances != null) {
            return;
        }
        synchronized (INIT_LOCK) {
            if (_cls_ecu_flags0._cls_ecu_flags0_instances == null) {
                _cls_ecu_flags0.initialize();
            }
        }
    }

    public static String onSample(EcuSample sample) {
        // Drive LARVA monitor explicitly to avoid relying on CTW state.
        ensureInitialized();
        _cls_ecu_flags0 monitor = _cls_ecu_flags0._get_cls_ecu_flags0_inst();
        if (monitor == null) {
            return null;
        }
        synchronized (_cls_ecu_flags0._cls_ecu_flags0_instances) {
            _cls_ecu_flags0.s = sample;
            monitor._call("JavaMonitorBridge.onSample", 0 /* sampleReceived */);
            monitor._call_all_filtered("JavaMonitorBridge.onSample", 0 /* sampleReceived */);
        }
        String state = monitor.getCurrentStateName();
        if ("ok".equals(state) || "timeBackwards".equals(state)) {
            return null;
        }
        return state;
    }
}
