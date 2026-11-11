package org.example.backend.auth.cert.dto;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;

@Data
public class CertApproveDTO {

    @NotBlank
    @Size(max = 128)
    private String subjectCn;

    @Size(max = 128)
    private String subjectO;

    @Size(max = 128)
    private String subjectOu;

    @NotNull
    @Min(1)
    @Max(3650)
    private Integer validDays;
}
