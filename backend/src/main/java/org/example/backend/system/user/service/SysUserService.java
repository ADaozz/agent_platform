package org.example.backend.system.user.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.system.user.dto.SysUserCreateDTO;
import org.example.backend.system.user.dto.SysUserQueryDTO;
import org.example.backend.system.user.dto.SysUserRoleAssignDTO;
import org.example.backend.system.user.dto.SysUserUpdateDTO;
import org.example.backend.system.user.entity.SysUserEntity;
import org.example.backend.system.user.vo.SysUserInfoVO;
import org.example.backend.system.user.vo.SysUserVO;

public interface SysUserService extends IService<SysUserEntity> {

    SysUserEntity getByUserName(String userName);

    /** 按邮箱精确查询（调用方需先规范化邮箱） */
    SysUserEntity getByEmail(String email);

    void createUser(SysUserCreateDTO dto);

    void updateUser(SysUserUpdateDTO dto);

    void deleteUser(Long userId);

    void assignUserRoles(SysUserRoleAssignDTO dto);

    SysUserVO getUserById(Long userId);

    SysUserInfoVO getCurrentUserInfo(Long userId);

    PageResultVO<SysUserVO> listUserInfo(SysUserQueryDTO dto);

    void updateLastLoginTime(Long userId);

    /** 校验用户存在且未停用，否则抛 AuthenticationException */
    void assertUserActive(Long userId);
}
