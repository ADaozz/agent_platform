package org.example.backend.auth.cert.dto;

import lombok.Data;

import javax.validation.constraints.Size;

@Data
public class CertApplyCreateDTO {

    @Size(max = 512)
    private String applyReason;
}
