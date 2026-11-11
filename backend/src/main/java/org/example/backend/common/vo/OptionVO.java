package org.example.backend.common.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 系统表（角色、权限等）下拉/多选选项：id 用于传参，label 用于展示。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class OptionVO {

    private Long id;

    private String label;
}
