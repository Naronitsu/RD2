package rd2.server.api;

import java.io.IOException;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import rd2.server.service.RvCsvService;
import rd2.server.service.RvResult;

@RestController
@RequestMapping("/api/rv")
public class RvController {

    private final RvCsvService rvCsvService;

    public RvController(RvCsvService rvCsvService) {
        this.rvCsvService = rvCsvService;
    }

    @PostMapping(path = "/analyze", consumes = MediaType.MULTIPART_FORM_DATA_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public RvResult analyze(
        @RequestParam("file") MultipartFile file,
        @RequestParam(value = "rvEnabled", required = false) Boolean rvEnabled
    ) throws IOException {
        return rvCsvService.analyze(file, rvEnabled);
    }
}
