package org.example.backend.auth.controller;

import org.example.backend.auth.dto.RegisterCodeDTO;
import org.example.backend.auth.dto.RegisterDTO;
import org.example.backend.auth.service.RegisterService;
import org.example.backend.common.annotation.Log;
import org.example.backend.common.enums.BusinessType;
import org.example.backend.common.enums.OperatorType;
import org.example.backend.common.result.AjaxResult;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import javax.validation.Valid;

@RestController
@Validated
public class RegisterController {

    @Autowired
    private RegisterService registerService;

    @Log(title = "注册", businessType = BusinessType.OTHER, operatorType = OperatorType.OTHER)
    @PostMapping("/register/code")
    public AjaxResult sendCode(@Valid @RequestBody RegisterCodeDTO dto) {
        registerService.sendCode(dto.getEmail());
        return AjaxResult.success("验证码已发送", null);
    }

    @Log(title = "注册", businessType = BusinessType.INSERT, operatorType = OperatorType.OTHER,
            excludeParamNames = {"passWord", "confirmPassWord", "code"})
    @PostMapping("/register")
    public AjaxResult register(@Valid @RequestBody RegisterDTO dto) {
        registerService.register(dto);
        return AjaxResult.success("注册成功", null);
    }
}
