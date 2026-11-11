package org.example.backend.asset.host.service;

import com.baomidou.mybatisplus.extension.service.IService;
import org.example.backend.asset.host.dto.VmHostQueryDTO;
import org.example.backend.asset.host.dto.VmHostUpdateDTO;
import org.example.backend.asset.host.entity.VmHostEntity;
import org.example.backend.asset.host.vo.VmHostVO;
import org.example.backend.common.vo.PageResultVO;

public interface VmHostService extends IService<VmHostEntity> {

    PageResultVO<VmHostVO> listVmHost(VmHostQueryDTO dto);

    void updateVmHost(VmHostUpdateDTO dto);
}
