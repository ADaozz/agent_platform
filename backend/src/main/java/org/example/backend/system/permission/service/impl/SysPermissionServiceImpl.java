package org.example.backend.system.permission.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.extern.slf4j.Slf4j;
import org.example.backend.common.vo.OptionVO;
import org.example.backend.common.vo.PageResultVO;
import org.example.backend.system.permission.dto.SysPermissionQueryDTO;
import org.example.backend.system.permission.entity.SysPermissionEntity;
import org.example.backend.system.permission.mapper.SysPermissionMapper;
import org.example.backend.system.permission.service.SysPermissionService;
import org.example.backend.system.permission.vo.SysPermissionVO;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.util.StringUtils;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

@Service
@Slf4j
public class SysPermissionServiceImpl extends ServiceImpl<SysPermissionMapper, SysPermissionEntity> implements SysPermissionService {

    @Resource
    private SysPermissionMapper sysPermissionMapper;

    @Override
    // 按权限ID查询权限
    public SysPermissionEntity getByPermissionId(Long PermissionId) {
        LambdaQueryWrapper<SysPermissionEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(
                SysPermissionEntity::getPermissionId,
                PermissionId
        );
        return sysPermissionMapper.selectOne(wrapper);
    }

    @Override
    // 查询用户拥有的权限标识列表
    public List<String> selectSysPermissionByUserId(Long userId) {
        return sysPermissionMapper.selectSysPermissionByUserId(userId);
    }

    @Override
    // 查询用户的权限选项列表
    public List<OptionVO> selectPermissionOptionsByUserId(Long userId) {
        return sysPermissionMapper.selectPermissionOptionsByUserId(userId);
    }

    @Override
    // 列出全部权限选项（管理员）
    public List<OptionVO> listAllPermissionOptions() {
        if (!org.apache.shiro.SecurityUtils.getSubject().hasRole("admin")) {
            throw new org.example.backend.common.exception.BusinessException(
                    org.example.backend.common.exception.Module.ModuleType.SYSTEM,
                    "仅管理员可以查看权限列表", null);
        }
        return sysPermissionMapper.selectAllPermissionOptions();
    }

    @Override
    // 分页查询权限列表
    public PageResultVO<SysPermissionVO> listPermissionInfo(SysPermissionQueryDTO dto) {
        if (!org.apache.shiro.SecurityUtils.getSubject().hasRole("admin")) {
            throw new org.example.backend.common.exception.BusinessException(
                    org.example.backend.common.exception.Module.ModuleType.SYSTEM,
                    "仅管理员可以查看权限列表", null);
        }
        if (dto.getPermissionId() != null) {
            SysPermissionEntity entity = getByPermissionId(dto.getPermissionId());
            if (entity == null) {
                return new PageResultVO<>(0, Collections.emptyList());
            }
            return new PageResultVO<>(1, Collections.singletonList(toVO(entity)));
        }
        LambdaQueryWrapper<SysPermissionEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.like(StringUtils.hasText(dto.getSysPermission()),
                        SysPermissionEntity::getSysPermission, dto.getSysPermission())
                .orderByAsc(SysPermissionEntity::getPermissionId);
        int pageNum = dto.getPageNum() == null ? 1 : dto.getPageNum();
        int pageSize = dto.getPageSize() == null ? 10 : dto.getPageSize();
        Page<SysPermissionEntity> page =
                sysPermissionMapper.selectPage(new Page<>(pageNum, pageSize), wrapper);
        List<SysPermissionVO> rows = page.getRecords().stream()
                .map(this::toVO)
                .collect(Collectors.toList());
        return new PageResultVO<>(page.getTotal(), rows);
    }

    // 将权限实体转换为VO
    private SysPermissionVO toVO(SysPermissionEntity entity) {
        SysPermissionVO vo = new SysPermissionVO();
        vo.setPermissionId(entity.getPermissionId());
        vo.setSysPermission(entity.getSysPermission());
        return vo;
    }
}
