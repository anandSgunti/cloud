# PII Deletion Solution - Options Analysis

**Requirement**: Delete images with human faces within 24 hours  
**Assessment Date**: February 27, 2026

---

## Solution Options Evaluated

| # | Option | Description | Advantages | Disadvantages | Recommendation |
|---|--------|-------------|------------|---------------|----------------|
| 1 | **Pre-Processing Detection & Routing** | Face detection before Transfer Bridge. Route to quarantine (face) or approved (no face). Hourly quarantine purge. | • Transfer Bridge unchanged<br>• Clear physical separation<br>• No wasted processing of PII<br>• Simple compliance verification<br>• Cost efficient | • Requires new pre-processing layer<br>• Additional Azure services | **SELECTED** |
| 2 | Post-Processing Detection | All images processed by Bridge first. Face detection after processing. Delete from final storage if face detected. | • Bridge processes all images<br>• Minimal workflow changes | • Bridge wastes resources on PII<br>• Larger storage requirements<br>• PII exists in processed form<br>• Higher compliance risk | REJECTED |
| 3 | Modify Transfer Bridge | Integrate face detection directly into Transfer Bridge code. Bridge handles detection and routing. | • Unified pipeline<br>• Single codebase | • Modifies $50k Bridge investment<br>• Political sensitivity<br>• Violates "unchanged" constraint<br>• Harder to rollback | REJECTED |

---

## Decision Criteria

| Criterion | Weight | Option 1 | Option 2 | Option 3 | 
|-----------|--------|----------|----------|----------|
| Transfer Bridge Unchanged | Critical | ✅ | ✅ | ❌ | 
| Compliance Safety | High | ✅ | ⚠️ | ✅ | 
| Implementation Feasibility | High | ✅ | ✅ | ✅ | 
| Operational Simplicity | Medium | ✅ | ✅ | ⚠️ | 
| Cost Efficiency | Medium | ✅ | ⚠️ | ✅ | 
| Political Acceptability | Critical | ✅ | ✅ | ❌ | 

**Legend**: ✅ Meets requirement | ⚠️ Partially meets | ❌ Does not meet

---

## Selected Solution: Option 1 - Pre-Processing Detection & Routing

### Justification

**Technical**:
- Preserves Transfer Bridge as-is (meets critical constraint)
- Physical container separation provides clear compliance boundary
- Avoids processing overhead on images destined for deletion
- Simple verification mechanism (quarantine blob count)

**Compliance**:
- Clear PII isolation in dedicated quarantine container
- Hard delete enforcement via hourly purge
- Auditable via Azure Table Storage timestamps
- Lifecycle policy provides failsafe mechanism

**Operational**:
- Azure-native services (Face API, Table Storage, Blob Storage)
- Automated workflow reduces human error
- Straightforward monitoring and alerting
- Low monthly operational cost (~$5)

**Political**:
- $50,000 Transfer Bridge investment fully preserved
- Solution presented as enhancement, not fix
- No criticism of existing architecture
- Maintains positive team relationships

### Trade-offs Accepted

- Additional pre-processing layer introduces new component
- Requires Azure Face API integration
- Bridge processes subset of images (acceptable given efficiency gain)

---

## Recommendation

**Approved Solution**: Option 1 - Pre-Processing Detection & Routing

**Implementation Priority**: High  
**Risk Level**: Low  
**Estimated Cost**: $5/month operational

---

**Prepared By**: [Assessment Candidate]  
**Date**: February 27, 2026  
**Status**: Approved for Implementation
